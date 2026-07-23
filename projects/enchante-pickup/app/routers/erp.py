"""ERP 대시보드 — 지점별 주문 보드 + 재고 + SSE 실시간 스트림."""
import logging
from datetime import datetime
from pathlib import Path

import httpx

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ..config import get_settings
from ..db import get_session
from ..events import broker
from ..imweb.client import ImwebClient
from ..models import InventoryItem, PickupOrder, Store

logger = logging.getLogger("uvicorn.error")

# ERP 상태 → 아임웹 shipping-operation enum (역방향 동기화)
# 배송없음 상품 기준: 픽업완료=배송완료 하나만 푸시 (픽업대기는 입금확인 시 자동)
IMWEB_PUSH_MAP = {"픽업완료": "SHIPPING_COMPLETE"}
# 택배 주문의 배송 전이는 순차만 허용 (스펙 에러표 30077/30084/30090 실측)
SHIP_SEQ = ["SHIPPING_READY", "SHIPPING", "SHIPPING_COMPLETE"]


def _imweb_error_message(exc: Exception) -> str:
    """httpx 에러에서 아임웹 error.message 추출."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            return response.json().get("error", {}).get("message", "") or str(exc)
        except Exception:  # noqa: BLE001
            return str(exc)
    return str(exc)


def _push_shipping_status(client: ImwebClient, order: PickupOrder, target: str) -> None:
    """아임웹 섹션 상태를 target으로 전이. 직행 우선, 실패 시 순차 폴백.

    - 배송없음(픽업) 주문: PREPARATION→COMPLETE 직행이 허용되는 것으로 보고 우선 시도
    - 택배 주문: 순차 규칙(READY→SHIPPING→COMPLETE, 배송중엔 송장 필요)로 폴백
    이미 target이면 no-op. 최종 실패는 raise (호출자가 사유 표면화).
    """
    fresh = client.get_order(order.order_no)
    sections = fresh.get("sections") or []
    current = sections[0].get("orderSectionStatus", "") if sections else ""
    if current == target:
        return
    try:
        client.set_section_shipping_status(order.order_no, order.section_code, target)
        return
    except Exception:  # noqa: BLE001 — 직행 불가 → 순차 폴백
        pass
    start = SHIP_SEQ.index(current) + 1 if current in SHIP_SEQ else 0
    end = SHIP_SEQ.index(target)
    if start > end:
        return  # 역방향(완료→대기 등)은 아임웹이 지원하지 않음 — 건너뜀
    for step in SHIP_SEQ[start : end + 1]:
        client.set_section_shipping_status(order.order_no, order.section_code, step)

router = APIRouter(prefix="/erp", tags=["erp"])

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "erp.html"


@router.get("", response_class=HTMLResponse)
def dashboard() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


@router.get("/api/stores")
def list_stores(session: Session = Depends(get_session)) -> list[str]:
    return [store.name for store in session.exec(select(Store)).all()]


@router.get("/api/orders")
def list_orders(
    store: str = "",
    session: Session = Depends(get_session),
) -> list[dict]:
    query = select(PickupOrder).order_by(PickupOrder.created_at.desc())
    if store:
        query = query.where(PickupOrder.store_name == store)
    return [order.model_dump() for order in session.exec(query).all()]


class StatusUpdate(BaseModel):
    status: str  # 결제대기/픽업대기/픽업완료/취소/반품


@router.post("/api/orders/{order_id}/status")
def update_status(
    order_id: int,
    body: StatusUpdate,
    session: Session = Depends(get_session),
) -> dict:
    order = session.get(PickupOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404)
    order.status = body.status
    order.updated_at = datetime.now()
    session.add(order)
    session.commit()

    # 역방향 동기화 (best-effort): 결제완료=입금확인, 상품준비/픽업대기/픽업완료=배송 상태(순차 전이)
    imweb_synced = False
    imweb_error = ""
    settings = get_settings()
    if settings.imweb_push_enabled and settings.imweb_client_id:
        try:
            client = ImwebClient(session)
            if body.status in IMWEB_PUSH_MAP and order.section_code:
                _push_shipping_status(client, order, IMWEB_PUSH_MAP[body.status])
                imweb_synced = True
            # 푸시 성공 시 해당 주문을 즉시 재조회해 아임웹 실상태를 바로 반영
            if imweb_synced:
                from .webhooks import ingest_order_payload

                fresh = client.get_order(order.order_no)
                ingest_order_payload(session, fresh, "API_SYNC")
                session.commit()
                session.refresh(order)
        except Exception as exc:  # noqa: BLE001 — 푸시 실패해도 ERP 상태는 유지
            imweb_error = _imweb_error_message(exc)
            logger.warning(
                "아임웹 상태 푸시 실패 %s(%s): %s", order.order_no, body.status, imweb_error
            )

    broker.publish(
        "status",
        {
            "order_no": order.order_no,
            "status": order.status,
            "store": order.store_name,
            "imweb_synced": imweb_synced,
        },
    )
    return {"ok": True, "imweb_synced": imweb_synced, "imweb_error": imweb_error}


@router.post("/api/orders/{order_id}/confirm-payment")
def confirm_payment(order_id: int, session: Session = Depends(get_session)) -> dict:
    """무통장 입금 확인 — 아임웹 입금완료 처리 후 실상태를 즉시 재동기화.

    드롭다운과 달리 실패를 명시적으로 반환한다(돈 관련 액션은 조용한 실패 금지).
    """
    order = session.get(PickupOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404)
    settings = get_settings()
    if not (settings.imweb_push_enabled and settings.imweb_client_id):
        raise HTTPException(status_code=400, detail="아임웹 푸시가 비활성화되어 있습니다")

    client = ImwebClient(session)
    try:
        # 이미 입금완료면 confirm 호출 없이 성공 처리 (30061 방지 — 멱등)
        fresh = client.get_order(order.order_no)
        payments = fresh.get("payments") or []
        already_paid = any(p.get("paymentStatus") == "PAYMENT_COMPLETE" for p in payments)
        if not already_paid:
            client.confirm_bank_transfer(order.order_no)
    except httpx.HTTPStatusError as exc:
        try:
            message = exc.response.json().get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            message = ""
        logger.warning(
            "입금확인 실패 %s: %s %s", order.order_no, exc.response.status_code, message
        )
        raise HTTPException(
            status_code=502,
            detail=f"아임웹 입금확인 실패: {message or exc.response.status_code}"
            " — Payment API 활성화와 /auth/login 재인가를 확인하세요",
        )
    except Exception as exc:  # noqa: BLE001 — 토큰 미발급 등
        raise HTTPException(status_code=502, detail=f"아임웹 입금확인 실패: {exc}")

    # 성공 — 아임웹 실상태를 즉시 읽어와 확정 반영
    from .webhooks import ingest_order_payload

    fresh = client.get_order(order.order_no)
    ingest_order_payload(session, fresh, "API_SYNC")
    session.commit()
    session.refresh(order)
    broker.publish(
        "status",
        {"order_no": order.order_no, "status": order.status,
         "store": order.store_name, "imweb_synced": True},
    )
    return {"ok": True, "status": order.status}


@router.get("/api/inventory")
def list_inventory(session: Session = Depends(get_session)) -> list[dict]:
    return [item.model_dump() for item in session.exec(select(InventoryItem)).all()]


class InventoryAdjust(BaseModel):
    delta: int


@router.post("/api/inventory/{item_id}/adjust")
def adjust_inventory(
    item_id: int,
    body: InventoryAdjust,
    session: Session = Depends(get_session),
) -> dict:
    item = session.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404)
    item.qty = max(0, item.qty + body.delta)
    session.add(item)
    session.commit()
    broker.publish("inventory", {"store": item.store_name, "product": item.product_name, "qty": item.qty})
    return {"ok": True, "qty": item.qty}


@router.get("/api/stream")
async def stream() -> StreamingResponse:
    return StreamingResponse(
        broker.subscribe(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
