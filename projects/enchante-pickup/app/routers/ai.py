"""AI 요약설명 프록시 — 크롬 확장 '상품 요약설명 도우미'용.

확장(공개 배포)에 API 키를 내장하지 않기 위해 서버가 Claude API를 대신 호출한다.
키는 서버 .env(ANTHROPIC_API_KEY)에만 존재하고, IP당 시간 단위 레이트리밋으로 남용을 막는다.
"""
import json
import re
import time

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import get_settings

router = APIRouter()

MODEL = "claude-haiku-4-5"
RATE_LIMIT = 20  # IP당 시간당 허용 요청 수
RATE_WINDOW = 3600.0
_hits: dict[str, list[float]] = {}


class SummaryRequest(BaseModel):
    name: str = ""
    cats: list[str] = []
    price: str = ""
    summary: str = ""
    keywords: str = ""
    tone: str = "정중한 — 격식 있고 신뢰감 있게"


def _build_prompt(body: SummaryRequest) -> str:
    lines = ["다음 상품의 쇼핑몰 요약설명(메타 디스크립션) 3안을 작성해라.", ""]
    # 모든 입력에 길이 상한을 둬 토큰 폭증(비용 증폭)을 막는다
    lines.append(f"상품명: {body.name.strip()[:120] or '(미입력)'}")
    if body.cats:
        lines.append("카테고리: " + ", ".join(c.strip()[:40] for c in body.cats[:5] if c.strip()))
    if body.price.strip():
        lines.append(f"판매가: {body.price.strip()[:20]}원")
    if body.summary.strip():
        lines.append(f"기존 요약설명(참고): {body.summary.strip()[:300]}")
    if body.keywords.strip():
        lines.append(f"특징 키워드(반드시 자연스럽게 반영): {body.keywords.strip()[:200]}")
    lines.append(f"톤: {body.tone.strip()[:60]}")
    lines += [
        "",
        "규칙:",
        "- 각 안은 한국어 80~160자, 1~2문장",
        "- 이모지·해시태그·최상급 과장 표현 금지",
        "- 상품명을 자연스럽게 포함",
        "- 세 안은 서로 문장 구조가 달라야 함",
        '- 출력은 JSON 문자열 배열만: ["안1","안2","안3"]',
    ]
    return "\n".join(lines)


@router.post("/api/summary")
async def generate_summary(body: SummaryRequest, request: Request) -> dict:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="AI 생성이 비활성화되어 있습니다")

    # Caddy 뒤에서는 request.client.host가 항상 프록시 IP라 전역 버킷이 된다 —
    # 신뢰하는 리버스프록시가 넣어준 X-Forwarded-For의 첫 IP를 우선 사용.
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    now = time.time()
    hits = [t for t in _hits.get(ip, []) if now - t < RATE_WINDOW]
    if len(hits) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요")
    hits.append(now)
    _hits[ip] = hits

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "content-type": "application/json",
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 600,
                    "system": "너는 한국 이커머스 상품의 요약설명(메타 디스크립션) 전문 카피라이터다. 반드시 JSON 문자열 배열만 출력한다.",
                    "messages": [{"role": "user", "content": _build_prompt(body)}],
                },
            )
    except httpx.HTTPError:
        # 타임아웃·연결 오류를 502로 정규화 — 미처리 예외는 CORS 헤더 없는 응답이 되어
        # 확장이 사유 없는 네트워크 오류만 보게 되므로 반드시 잡는다.
        raise HTTPException(status_code=502, detail="AI 서버에 연결하지 못했습니다")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="AI 생성에 실패했습니다")

    data = resp.json()
    raw = ((data.get("content") or [{}])[0].get("text") or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\s*", "", raw, flags=re.I)
        raw = re.sub(r"```\s*$", "", raw).strip()
    try:
        arr = json.loads(raw)
    except (ValueError, TypeError):
        arr = None
    # 배열이 아니면(모델이 문자열 하나만 반환하는 등) 거부 — 문자열을 글자 단위로 순회해
    # 한 글자짜리 '초안'이 나오는 것을 막는다.
    drafts = (
        [x.strip() for x in arr if isinstance(x, str) and x.strip()][:5]
        if isinstance(arr, list)
        else []
    )
    if not drafts:
        raise HTTPException(status_code=502, detail="AI 응답 형식 오류")
    return {"drafts": drafts}
