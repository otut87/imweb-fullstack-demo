"""쇼핑몰 상세페이지에서 호출하는 공개 조회 API (지점별 재고 노출용).

CORS는 main.py에서 support51251.imweb.me 오리진에 GET만 허용.
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
