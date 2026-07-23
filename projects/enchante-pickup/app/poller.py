"""아임웹 주문 API 폴링 — 웹훅 미수신 환경(앱 심사 전) 폴백.

실측(2026-07-23): 테스트연동 상태에서 웹훅 '테스트 보내기'는 수신되지만
실제 주문 이벤트는 전송되지 않음 (개발자센터 문구: "API 승인 후 사이트에서
발생하는 이벤트가 전송"). 심사 승인 전까지 주문 목록을 주기 폴링해
웹훅과 동일한 파이프라인(ingest_order_payload)으로 주입한다.
승인 후 웹훅이 켜져도 upsert 기반이라 중복 없이 공존한다.
"""
import asyncio
import logging

from sqlmodel import Session

from sqlmodel import select

from .config import get_settings
from .db import get_engine
from .events import broker
from .imweb.client import ImwebClient
from .models import PickupOrder
from .routers.webhooks import (
    enrich_member_grade,
    ingest_order_payload,
    order_event_message,
)

logger = logging.getLogger("uvicorn.error")


def _poll_once() -> list[dict]:
    """주문 목록 1페이지 동기화. 변경된 주문의 SSE 메시지 목록을 반환."""
    messages: list[dict] = []
    with Session(get_engine()) as session:
        client = ImwebClient(session)
        data = client.list_orders(page=1, limit=50)
        for order in data.get("list") or []:
            row, is_new, changed = ingest_order_payload(session, order, "API_POLL")
            if row is None:
                continue
            session.commit()
            if changed:
                session.refresh(row)
                message = order_event_message(row, is_new)
                messages.append(message)
                if is_new:
                    from .kakao import send_order_alert

                    send_order_alert(session, message)  # 운영자 카톡 알림

        # 회원 등급 보강 (Member-Info API) — 미보강 주문만, 사이클당 최대 5건
        pending = session.exec(
            select(PickupOrder)
            .where(PickupOrder.member_uid != "", PickupOrder.member_grade == "")
            .limit(5)
        ).all()
        enriched = False
        for row in pending:
            try:
                enriched = enrich_member_grade(session, client, row) or enriched
            except Exception as exc:  # noqa: BLE001 — scope 미부여 등은 다음 재인가 후 해소
                logger.warning("회원 등급 보강 실패 %s: %s", row.order_no, exc)
                break  # 권한 문제면 이번 사이클 중단
        if enriched:
            messages.append({"_refresh": True})
    return messages


async def poll_orders_forever(stop: asyncio.Event) -> None:
    settings = get_settings()
    interval = max(10, settings.imweb_poll_interval)
    logger.info("주문 폴링 시작 (interval=%ss)", interval)
    while True:
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            logger.info("주문 폴링 종료")
            return
        except asyncio.TimeoutError:
            pass
        try:
            messages = await asyncio.to_thread(_poll_once)
            for message in messages:  # 이벤트 루프 스레드에서만 publish
                if message.get("_refresh"):
                    broker.publish("status", {"refresh": True})
                else:
                    broker.publish("order", message)
            if messages:
                logger.info("폴링 반영: %s건 변경", len(messages))
        except Exception as exc:  # noqa: BLE001 — 폴링 실패는 다음 주기에 재시도
            logger.warning("주문 폴링 실패: %s", exc)
