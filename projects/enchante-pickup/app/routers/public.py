"""쇼핑몰 상세페이지에서 호출하는 공개 조회 API (지점별 재고 노출용).

이 엔드포인트는 GET 전용이며 상세페이지(support51251.imweb.me)에서 호출된다.
CORS 허용 오리진·메서드는 main.py의 단일 CORSMiddleware에서 관리한다
(쇼핑몰 오리진 + 크롬 확장 오리진, GET·POST 공통).
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import InventoryItem

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/stock")
def stock_by_product(product: str, session: Session = Depends(get_session)) -> list[dict]:
    """상품명 기준 지점별 재고 — 상세페이지 지점 버튼에 표시."""
    rows = session.exec(
        select(InventoryItem).where(InventoryItem.product_name == product)
    ).all()
    return [{"store": r.store_name, "qty": r.qty} for r in rows]
