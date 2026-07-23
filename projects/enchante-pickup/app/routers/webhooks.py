"""아임웹 웹훅 수신 → 원본 저장 → 주문 파싱 → 지점 라우팅/재고 차감 → SSE 브로드캐스트.

문서 근거: 웹훅은 개발자센터에서 이벤트별로 수신 URL 1개 등록.
주문 계열 이벤트 30+종 (생성/입금완료/배송/취소/반품/교환/환불 ...).
페이로드 스펙은 문서 미공개 → 원본을 WebhookEvent에 전량 보존하고,
파서는 키 이름에 유연한 deep-scan 방식으로 구현. 실수신 후 정확한 스펙으로 조여갈 것.
(개발자센터 '테스트 보내기'로 샘플 페이로드를 먼저 받아볼 수 있음)
"""
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select

from ..config import get_settings
from ..db import SEED_QTY, get_session
from ..events import broker
from ..models import InventoryItem, PickupOrder, WebhookEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# 지점/날짜 옵션을 찾을 때 쓰는 키워드 (Enchanté 상품 옵션명 기준)
STORE_KEYWORDS = ("픽업 지점", "픽업지점", "지점", "매장")
DATE_KEYWORDS = ("픽업 희망일", "픽업일", "픽업 날짜", "희망일")


def _walk(node: Any):
    """중첩 JSON의 모든 dict를 순회."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _find_option_value(payload: Any, keywords: tuple[str, ...]) -> str:
    """옵션 값 추출.

    실스펙(2026-07-23 웹훅 테스트로 확인): productInfo.optionInfo가
    {"옵션명": "값"} 평면 dict — 키에 키워드가 포함되면 값을 반환.
    구형 name/value 쌍 구조도 폴백으로 지원.
    """
    for node in _walk(payload):
        for key, value in node.items():
            if isinstance(value, (str, int, float)) and any(
                keyword in str(key) for keyword in keywords
            ):
                if str(value):
                    return str(value)
    # 폴백: {name: 옵션명, value: 값} 쌍 구조
    name_keys = ("name", "optionName", "option_name", "title", "label")
    value_keys = ("value", "optionValue", "option_value", "valueName", "text")
    for node in _walk(payload):
        name = next((str(node[k]) for k in name_keys if node.get(k)), "")
        if name and any(keyword in name for keyword in keywords):
            value = next((str(node[k]) for k in value_keys if node.get(k)), "")
            if value:
                return value
    return ""


def _first_str(payload: Any, keys: tuple[str, ...]) -> str:
    for node in _walk(payload):
        for key in keys:
            if node.get(key):
                return str(node[key])
    return ""


def _first_int(payload: Any, keys: tuple[str, ...]) -> int:
    for node in _walk(payload):
        for key in keys:
            value = node.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return int(value)
    return 0


# ERP 상태 진행 순서 — 폴링/웹훅이 수동 진행 상태를 되돌리지 않게 하는 랭크
STATUS_RANK = {"결제대기": 0, "픽업대기": 1, "픽업완료": 2}


def _map_status(event_type: str, payload: Any) -> str:
    """아임웹 이벤트/섹션/결제 상태 → ERP 픽업 상태 (배송없음 상품 기준 5종).

    | ERP      | 아임웹                                        |
    | 결제대기 | 무통장 입금 전 (카드 결제는 자동 통과)          |
    | 픽업대기 | 입금완료 + 상품준비중 (PRODUCT_PREPARATION)     |
    | 픽업완료 | 배송완료 (SHIPPING_COMPLETE)                   |
    | 취소/반품 | 취소/반품 계열 이벤트                          |

    - 결제 판정: payments[].paymentStatus == PAYMENT_COMPLETE (실측) 또는 입금 이벤트명.
    - 구 택배 주문의 SHIPPING_READY/SHIPPING 은 픽업대기로 흡수.
    - isCancelReq는 '취소 신청 가능 여부'라 상태 판단에 쓰지 않는다.
    """
    section_status = _first_str(payload, ("orderSectionStatus",))
    text = f"{event_type} {section_status}".upper()
    if "RETURN" in text:
        return "반품"
    if "CANCEL" in text:
        return "취소"
    if "SHIPPING_COMPLETE" in text or "DELIVERY_COMPLETE" in text:
        return "픽업완료"
    if "SHIPPING" in text or "DELIVERY" in text:
        return "픽업대기"
    if (
        _first_str(payload, ("paymentStatus",)) == "PAYMENT_COMPLETE"
        or "DEPOSIT" in text
        or "PAYMENT_COMPLETE" in text
    ):
        return "픽업대기"
    return "결제대기"


def _items_summary(payload: Any) -> str:
    names = []
    for node in _walk(payload):
        name = node.get("prodName") or node.get("productName") or node.get("prod_name")
        if name and str(name) not in names:
            names.append(str(name))
    if not names:
        return ""
    return names[0] + (f" 외 {len(names) - 1}건" if len(names) > 1 else "")


@router.post("/imweb")
async def receive_imweb_webhook(
    request: Request,
    secret: str = Query(""),
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    if settings.webhook_shared_secret and secret != settings.webhook_shared_secret:
        raise HTTPException(status_code=403, detail="secret 불일치")
    # 아임웹 인증정보 검증 — authorization 헤더에 개발자센터 '인증 정보' 값이 그대로 옴(실확인)
    if settings.imweb_webhook_auth:
        if request.headers.get("authorization", "") != settings.imweb_webhook_auth:
            raise HTTPException(status_code=403, detail="아임웹 인증정보 불일치")

    raw = (await request.body()).decode("utf-8", errors="replace")
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}

    event_type = _first_str(payload, ("event", "eventType", "event_type", "topic", "type"))

    # 1) 원본 전량 보존 (스펙 확인/재처리용) — 헤더 포함(아임웹 인증정보 위치 확인)
    headers = dict(request.headers.items())
    session.add(
        WebhookEvent(
            event_type=event_type,
            raw_body=raw,
            headers_json=json.dumps(headers, ensure_ascii=False),
        )
    )

    # 2) 주문 파싱·upsert·재고 (웹훅/폴링 공용 파이프라인)
    row, is_new, _changed = ingest_order_payload(session, payload, event_type)
    if row is None:
        session.commit()
        return {"ok": True, "handled": "logged-only"}

    session.commit()
    session.refresh(row)
    message = order_event_message(row, is_new)
    broker.publish("order", message)
    if is_new:
        from ..kakao import send_order_alert

        send_order_alert(session, message)  # 운영자 카톡 알림 (실패해도 무해)
    return {"ok": True, "order_no": row.order_no, "store": row.store_name}


def order_event_message(row: PickupOrder, is_new: bool) -> dict:
    """SSE 'order' 이벤트 페이로드 (웹훅/폴링 공용)."""
    return {
        "order_no": row.order_no,
        "event_type": row.event_type,
        "status": row.status,
        "store": row.store_name,
        "pickup_date": row.pickup_date,
        "customer": row.customer_name,
        "items": row.items_summary,
        "amount": row.amount,
        "is_new": is_new,
    }


def ingest_order_payload(
    session: Session, payload: Any, event_type: str
) -> tuple[PickupOrder | None, bool, bool]:
    """주문성 페이로드를 PickupOrder로 upsert + 신규 시 재고 차감.

    웹훅 이벤트(data.section...)와 주문 API 응답(list[] 원소) 모두
    deep-scan 기반이라 동일하게 처리된다. returns (row, is_new, changed).
    """
    order_no = _first_str(payload, ("orderNo", "order_no", "orderNumber", "orderCode"))
    if not order_no:
        return None, False, False

    store = _find_option_value(payload, STORE_KEYWORDS) or "미지정"
    pickup_date = _find_option_value(payload, DATE_KEYWORDS)

    row = session.exec(
        select(PickupOrder).where(PickupOrder.order_no == order_no)
    ).first()
    is_new = row is None
    if row is None:
        row = PickupOrder(order_no=order_no)
    before = (row.status, row.store_name, row.pickup_date, row.amount)
    row.event_type = event_type
    row.section_code = _first_str(payload, ("orderSectionCode",)) or row.section_code
    row.store_name = store if store != "미지정" else row.store_name
    row.pickup_date = pickup_date or row.pickup_date
    row.customer_name = (
        _first_str(payload, ("ordererName", "orderer_name", "memberName", "name"))
        or row.customer_name
    )
    row.member_uid = _first_str(payload, ("memberUid",)) or row.member_uid
    row.items_summary = _items_summary(payload) or row.items_summary
    row.amount = (
        _first_int(payload, ("totalPaymentPrice", "paymentAmount", "totalPrice", "amount", "price"))
        or row.amount
    )
    # 상태 반영 — 취소/반품은 무조건, 진행 상태는 앞으로만 (폴링이 ERP 수동 진행을 되돌리지 않게)
    mapped = _map_status(event_type, payload)
    if mapped in ("취소", "반품") or STATUS_RANK.get(mapped, 0) >= STATUS_RANK.get(row.status, 0):
        row.status = mapped
    row.updated_at = datetime.now()
    session.add(row)

    # 신규 주문이면 해당 지점 재고 차감
    # 실스펙: sectionItems[] = {qty, productInfo: {prodName, ...}} — qty는 아이템 레벨
    if is_new and row.store_name != "미지정":
        for node in _walk(payload):
            product_info = node.get("productInfo")
            if isinstance(product_info, dict) and product_info.get("prodName"):
                name = str(product_info["prodName"])
                qty = int(node.get("qty") or 1)
            elif node.get("prodName") and ("qty" in node or "count" in node):
                # 폴백(구형 평면 구조) — productInfo 하위 노드 이중 차감 방지 위해 qty 보유 노드만
                name = str(node["prodName"])
                qty = int(node.get("qty") or node.get("count") or 1)
            else:
                continue
            inv = session.exec(
                select(InventoryItem).where(
                    InventoryItem.store_name == row.store_name,
                    InventoryItem.product_name == name,
                )
            ).first()
            if inv is None:
                # 시드에 없는 상품은 첫 주문 때 자동 생성 (기본 재고에서 차감 시작)
                inv = InventoryItem(
                    store_name=row.store_name, product_name=name, qty=SEED_QTY
                )
            inv.qty = max(0, inv.qty - qty)
            session.add(inv)

    changed = is_new or before != (row.status, row.store_name, row.pickup_date, row.amount)
    return row, is_new, changed


def enrich_member_grade(session: Session, client, row: PickupOrder) -> bool:
    """회원 API(Member-Info)로 주문 고객의 쇼핑 등급을 보강. 성공 시 True.

    - 응답 필드 명칭 유연 대응(grade 계열 deep-scan)
    - 404(30001) = 운영진/비회원 주문 → '운영자'로 표시 (직원 주문 구분, 재시도 방지)
    """
    if not row.member_uid or row.member_grade:
        return False
    try:
        member = client.get_member(row.member_uid)
    except Exception as exc:  # noqa: BLE001
        response = getattr(exc, "response", None)
        if response is not None and response.status_code == 404:
            row.member_grade = "운영자"
            row.updated_at = datetime.now()
            session.add(row)
            session.commit()
            return True
        raise  # 권한/기타 오류는 호출자에서 처리
    grade = _first_str(
        member,
        ("shopGradeName", "gradeName", "memberGradeName", "shopGrade", "grade"),
    )
    if not grade:
        return False
    row.member_grade = grade
    row.updated_at = datetime.now()
    session.add(row)
    session.commit()
    return True
