"""Enchanté 지점 픽업 ERP — 아임웹 풀스택 데모 백엔드.

플로우: 아임웹 주문(픽업 지점/희망일 옵션) → 웹훅 수신 → 지점 라우팅/재고 차감
       → ERP 대시보드 실시간 반영(SSE). Open API로 주문 상세 보강 조회.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import get_settings
from .db import init_db
from .poller import poll_orders_forever
from .routers import auth, erp, public, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    stop = asyncio.Event()
    poll_task = None
    if settings.imweb_poll_enabled and settings.imweb_client_id:
        poll_task = asyncio.create_task(poll_orders_forever(stop))
    yield
    stop.set()
    if poll_task:
        await poll_task


app = FastAPI(title="Enchanté Pickup ERP", lifespan=lifespan)
# 상세페이지(쇼핑몰 오리진)에서 공개 재고 API 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://support51251.imweb.me"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(erp.router)
app.include_router(public.router)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse("/erp")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
