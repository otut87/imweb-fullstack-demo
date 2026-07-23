"""ERP 대시보드 실시간 갱신용 in-process pub/sub (SSE 브로커)."""
import asyncio
import json
from typing import AsyncGenerator


class Broker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def publish(self, event: str, data: dict) -> None:
        """모든 구독자에게 이벤트 전송. (웹훅 수신 스레드에서 호출해도 안전)"""
        message = {"event": event, "data": data}
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass  # 밀린 구독자는 스킵 — 대시보드는 재조회로 복구

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: {message['event']}\ndata: {json.dumps(message['data'], ensure_ascii=False, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # 프록시 타임아웃 방지 핑
        finally:
            self._subscribers.discard(queue)


broker = Broker()
