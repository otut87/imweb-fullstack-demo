"""ERP 대시보드 실시간 갱신용 in-process pub/sub (SSE 브로커)."""
import asyncio
import json
from typing import AsyncGenerator


class Broker:
    def __init__(self) -> None:
        # 구독자별 (큐, 그 큐가 속한 이벤트 루프) — 루프를 함께 보관해야
        # 스레드풀에서 호출돼도 루프에 안전하게 위임할 수 있다.
        self._subscribers: dict[asyncio.Queue, asyncio.AbstractEventLoop] = {}

    def publish(self, event: str, data: dict) -> None:
        """모든 구독자에게 이벤트 전송.

        ERP의 동기 def 엔드포인트는 FastAPI 스레드풀에서 실행되므로, 큐를 직접
        조작하면 루프 스레드의 wait_for 취소와 경합해 InvalidStateError가 날 수 있다.
        각 큐의 소속 루프에 call_soon_threadsafe로 위임해 항상 루프 스레드에서 넣는다.
        """
        message = {"event": event, "data": data}
        for queue, loop in list(self._subscribers.items()):
            def _put(q: asyncio.Queue = queue) -> None:
                try:
                    q.put_nowait(message)
                except asyncio.QueueFull:
                    pass  # 밀린 구독자는 스킵 — 대시보드는 재조회로 복구
            try:
                loop.call_soon_threadsafe(_put)
            except RuntimeError:
                pass  # 루프가 이미 닫힘 — 구독 종료 처리에 맡김

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers[queue] = asyncio.get_running_loop()
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: {message['event']}\ndata: {json.dumps(message['data'], ensure_ascii=False, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # 프록시 타임아웃 방지 핑
        finally:
            self._subscribers.pop(queue, None)


broker = Broker()
