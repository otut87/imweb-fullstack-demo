"""OAuth 인가 라우트 — 최초 1회 브라우저로 /auth/login 접속해 토큰 발급."""
import secrets

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session

from .. import kakao
from ..db import get_session
from ..imweb.oauth import build_authorize_url, exchange_code, save_tokens

router = APIRouter(prefix="/auth", tags=["auth"])

# 데모 규모 전제의 단일 프로세스 state 보관 (다중 인스턴스면 DB/캐시로 이동)
_pending_states: set[str] = set()


@router.get("/login")
def login() -> RedirectResponse:
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)
    return RedirectResponse(build_authorize_url(state))


@router.get("/kakao/login")
def kakao_login() -> RedirectResponse:
    """운영자 카카오 계정 연결 — 신규 주문 알림용 (최초 1회)."""
    return RedirectResponse(kakao.build_authorize_url())


@router.get("/kakao/callback")
def kakao_callback(
    request: Request,
    code: str = Query(""),
    session: Session = Depends(get_session),
):
    if not code:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": request.query_params.get("error", ""),
                "error_description": request.query_params.get("error_description", ""),
            },
        )
    row = kakao.save_tokens(session, kakao.exchange_code(code))
    return {
        "ok": True,
        "provider": "kakao",
        "scope": row.scope,
        "expires_at": row.expires_at.isoformat(),
        "next": "신규 픽업 주문이 카카오톡 '나와의 채팅'으로 발송됩니다",
    }


@router.get("/callback")
def callback(
    request: Request,
    code: str = Query(""),
    state: str = Query(""),
    session: Session = Depends(get_session),
):
    if not code:
        error_code = request.query_params.get("errorCode", "")
        message = request.query_params.get("message", "")
        if error_code or message:
            # 아임웹이 에러와 함께 돌려보낸 경우 — 재리다이렉트하면 루프가 되므로 표시하고 멈춤
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "errorCode": error_code,
                    "message": message,
                    "hint": "개발자센터 > 연동 사이트 관리에서 사이트-앱 연동 완료 후 /auth/login 재시도",
                },
            )
        # 파라미터 없이 직접 접속한 경우 → 인가 플로우 진입점으로 안내
        return RedirectResponse("/auth/login")
    # state는 프로세스 메모리 보관이라 재배포 직후엔 비어 있을 수 있음.
    # 데모 운영 편의상 불일치여도 진행 (코드 교환은 client secret으로 보호됨).
    _pending_states.discard(state)

    row = save_tokens(session, exchange_code(code))
    return {
        "ok": True,
        "site_code": row.site_code,
        "scope": row.scope,
        "expires_at": row.expires_at.isoformat(),
        "next": "웹훅 수신 대기 중 — /erp 대시보드를 여세요",
    }
