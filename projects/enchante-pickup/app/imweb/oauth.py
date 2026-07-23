"""아임웹 OAuth 2.0 — 인가/토큰 발급/갱신.

문서 근거 (developers-docs.imweb.me → 개발 가이드 → OAuth 2.0):
- 인가:   GET  {oauth_base}/oauth2/authorize
          ?responseType=code&clientId=..&redirectUri=..&scope=..&siteCode=..&state=..
- 토큰:   POST {oauth_base}/oauth2/token   grantType=authorization_code | refresh_token
- 파라미터는 camelCase (표준 OAuth의 snake_case 아님 — 주의)
- access token 2시간 / refresh token 90일
- rate limit: 버킷 25, 초당 2 회복 (X-RateLimit-* 헤더)

TODO(확인): 토큰 요청 본문이 JSON인지 form-urlencoded인지 문서 미명시.
아래는 JSON으로 구현 — 400 응답 시 form으로 전환해 재시도한다.
"""
import threading
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlmodel import Session, select

from ..config import get_settings
from ..models import OAuthToken

ACCESS_TOKEN_TTL = timedelta(hours=2)
REFRESH_MARGIN = timedelta(minutes=5)  # 만료 5분 전부터 선제 갱신

# refresh token은 사용 시 회전(재발급)되므로, 폴러 스레드와 요청 스레드가 동시에
# 같은 refresh token으로 갱신하면 한쪽이 무효화된 토큰으로 400 실패한다.
# 갱신 구간을 프로세스 전역 락으로 직렬화한다(데모=단일 워커 전제).
_refresh_lock = threading.Lock()


def _reload_token(session: Session, site_code: str) -> "OAuthToken | None":
    """다른 스레드/세션이 회전시킨 최신 토큰을 확실히 읽는다(identity map 우회)."""
    row = session.exec(
        select(OAuthToken).where(OAuthToken.site_code == site_code)
    ).first()
    if row is not None:
        session.refresh(row)
    return row


def build_authorize_url(state: str) -> str:
    s = get_settings()
    query = urlencode(
        {
            "responseType": "code",
            "clientId": s.imweb_client_id,
            "redirectUri": s.imweb_redirect_uri,
            "scope": s.imweb_scope,
            "siteCode": s.imweb_site_code,
            "state": state,
        }
    )
    return f"{s.imweb_oauth_base}/oauth2/authorize?{query}"


def _post_token(payload: dict) -> dict:
    """토큰 엔드포인트 호출. JSON 우선, 실패 시 form 재시도."""
    s = get_settings()
    url = f"{s.imweb_oauth_base}/oauth2/token"
    with httpx.Client(timeout=15) as client:
        response = client.post(url, json=payload)
        if response.status_code == 400:
            response = client.post(url, data=payload)
        response.raise_for_status()
        return response.json()


def exchange_code(code: str) -> dict:
    """인가 코드 → 토큰 발급."""
    s = get_settings()
    return _post_token(
        {
            "grantType": "authorization_code",
            "clientId": s.imweb_client_id,
            "clientSecret": s.imweb_client_secret,
            "redirectUri": s.imweb_redirect_uri,
            "code": code,
        }
    )


def refresh_token(refresh: str) -> dict:
    """refresh token → 토큰 갱신 (refresh token도 함께 재발급됨)."""
    s = get_settings()
    return _post_token(
        {
            "grantType": "refresh_token",
            "clientId": s.imweb_client_id,
            "clientSecret": s.imweb_client_secret,
            "refreshToken": refresh,
        }
    )


def _extract(body: dict, key: str) -> str:
    """응답 래핑 구조가 달라도 견디게 top-level/data 하위 모두 조회."""
    if key in body:
        return body[key]
    data = body.get("data")
    if isinstance(data, dict) and key in data:
        return data[key]
    raise KeyError(f"토큰 응답에서 {key}를 찾지 못함: {list(body.keys())}")


def save_tokens(session: Session, body: dict) -> OAuthToken:
    """토큰 응답을 DB에 저장(사이트당 1행 upsert)."""
    s = get_settings()
    access = _extract(body, "accessToken")
    refresh = _extract(body, "refreshToken")
    scope = body.get("scope") or (body.get("data") or {}).get("scope") or ""
    if isinstance(scope, list):
        scope = " ".join(scope)

    row = session.exec(
        select(OAuthToken).where(OAuthToken.site_code == s.imweb_site_code)
    ).first()
    if row is None:
        row = OAuthToken(site_code=s.imweb_site_code)
    row.access_token = access
    row.refresh_token = refresh
    row.scope = scope
    row.expires_at = datetime.now() + ACCESS_TOKEN_TTL
    row.updated_at = datetime.now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_valid_access_token(session: Session) -> str:
    """유효한 access token 반환 — 만료 임박 시 자동 갱신(락+더블체크)."""
    s = get_settings()
    row = session.exec(
        select(OAuthToken).where(OAuthToken.site_code == s.imweb_site_code)
    ).first()
    if row is None or not row.refresh_token:
        raise RuntimeError("토큰 없음 — /auth/login 으로 최초 인가부터 진행하세요.")
    if datetime.now() >= row.expires_at - REFRESH_MARGIN:
        with _refresh_lock:
            # 락 진입 후 재조회 — 대기 중 다른 스레드가 이미 갱신했으면 그대로 사용
            row = _reload_token(session, s.imweb_site_code) or row
            if datetime.now() >= row.expires_at - REFRESH_MARGIN:
                row = save_tokens(session, refresh_token(row.refresh_token))
    return row.access_token


def force_refresh_access_token(session: Session) -> str:
    """401 대응 — 현재 access token이 거부됐을 때 강제 갱신.

    락으로 직렬화하고, 락 진입 후 재조회해 stale refresh token 사용을 방지한다.
    대기 중 다른 스레드가 방금 갱신했으면(토큰 갱신 시각이 최근) 재갱신을 건너뛴다.
    """
    s = get_settings()
    with _refresh_lock:
        row = _reload_token(session, s.imweb_site_code)
        if row is None or not row.refresh_token:
            raise RuntimeError("토큰 없음 — /auth/login 으로 최초 인가부터 진행하세요.")
        # 대기 중 다른 스레드가 방금(10초 내) 갱신했으면 그 토큰이 유효 — 중복 회전 방지
        if datetime.now() - row.updated_at < timedelta(seconds=10):
            return row.access_token
        row = save_tokens(session, refresh_token(row.refresh_token))
    return row.access_token
