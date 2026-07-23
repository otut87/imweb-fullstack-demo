"""카카오 OAuth + '나에게 보내기' — 운영자(지점 담당자) 주문 알림.

- 신규 픽업 주문이 들어오면 연결된 카카오 계정의 '나와의 채팅'으로 알림 발송.
- 토큰은 아임웹과 동일 패턴으로 OAuthToken 테이블에 보관 (site_code='__kakao__' 행).
- 실서비스 전환 시 고객 대상 알림은 알림톡(카카오 비즈메시지)으로 확장한다.

스펙: https://kauth.kakao.com (인가/토큰, form-urlencoded),
      POST https://kapi.kakao.com/v2/api/talk/memo/default/send (template_object)
      access token 약 6시간, refresh token 약 2개월(갱신 응답에 없으면 기존 유지).
"""
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlmodel import Session, select

from .config import get_settings
from .models import OAuthToken

KAKAO_ROW_KEY = "__kakao__"  # OAuthToken.site_code 슬롯
AUTH_BASE = "https://kauth.kakao.com"
API_BASE = "https://kapi.kakao.com"
REFRESH_MARGIN = timedelta(minutes=10)

logger = logging.getLogger("uvicorn.error")


def build_authorize_url() -> str:
    settings = get_settings()
    query = urlencode(
        {
            "client_id": settings.kakao_rest_api_key,
            "redirect_uri": settings.kakao_redirect_uri,
            "response_type": "code",
            "scope": "talk_message",
        }
    )
    return f"{AUTH_BASE}/oauth/authorize?{query}"


def exchange_code(code: str) -> dict:
    settings = get_settings()
    response = httpx.post(
        f"{AUTH_BASE}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": settings.kakao_rest_api_key,
            "redirect_uri": settings.kakao_redirect_uri,
            "code": code,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _refresh(refresh_token: str) -> dict:
    settings = get_settings()
    response = httpx.post(
        f"{AUTH_BASE}/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": settings.kakao_rest_api_key,
            "refresh_token": refresh_token,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def save_tokens(session: Session, body: dict) -> OAuthToken:
    row = session.exec(
        select(OAuthToken).where(OAuthToken.site_code == KAKAO_ROW_KEY)
    ).first()
    if row is None:
        row = OAuthToken(site_code=KAKAO_ROW_KEY)
    row.access_token = body["access_token"]
    # 카카오는 만료 임박 전 갱신 시 refresh_token을 생략할 수 있음 — 기존 값 유지
    row.refresh_token = body.get("refresh_token") or row.refresh_token
    row.scope = body.get("scope", row.scope) or ""
    row.expires_at = datetime.now() + timedelta(seconds=int(body.get("expires_in", 21600)))
    row.updated_at = datetime.now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _valid_token(session: Session) -> str | None:
    row = session.exec(
        select(OAuthToken).where(OAuthToken.site_code == KAKAO_ROW_KEY)
    ).first()
    if row is None or not row.access_token:
        return None  # 아직 미연결
    if datetime.now() >= row.expires_at - REFRESH_MARGIN:
        row = save_tokens(session, _refresh(row.refresh_token))
    return row.access_token


def format_order_alert(message: dict) -> str:
    """SSE order 이벤트 페이로드(dict) → 카톡 알림 텍스트."""
    lines = [
        f"[{message.get('store', '미지정')}] 신규 픽업 주문",
        message.get("items") or "상품 정보 없음",
        f"픽업 {message.get('pickup_date') or '미지정'}",
        f"{message.get('customer') or '고객'} · {int(message.get('amount') or 0):,}원",
        f"No.{message.get('order_no', '')}",
    ]
    return "\n".join(lines)


def send_order_alert(session: Session, message: dict) -> bool:
    """신규 주문 알림 발송 — 미연결/실패 시 False (주문 파이프라인에 영향 없음)."""
    try:
        token = _valid_token(session)
        if token is None:
            return False
        settings = get_settings()
        erp_url = f"https://{settings.imweb_redirect_uri.split('/')[2]}/erp" \
            if settings.imweb_redirect_uri.startswith("http") else ""
        template = {
            "object_type": "text",
            "text": format_order_alert(message),
            "link": {"web_url": erp_url, "mobile_web_url": erp_url},
            "button_title": "ERP 열기",
        }
        response = httpx.post(
            f"{API_BASE}/v2/api/talk/memo/default/send",
            headers={"Authorization": f"Bearer {token}"},
            data={"template_object": json.dumps(template, ensure_ascii=False)},
            timeout=15,
        )
        response.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001 — 알림 실패는 로그만
        logger.warning("카카오 알림 실패: %s", exc)
        return False
