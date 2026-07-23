"""SQLite 엔진/세션 + 초기 시드."""
from sqlmodel import Session, SQLModel, create_engine, select

from .config import get_settings
from .models import InventoryItem, Store

_engine = None

SEED_STORES = ["강남점", "성수점", "천안점"]
SEED_PRODUCTS = [
    "Radiant Glow Serum I",
    "Radiant Glow Serum II",
    "Luminé Allure Body Lotion I",
    "Luminé Allure Body Lotion II",
]
SEED_QTY = 20


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            f"sqlite:///{settings.db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    # 경량 마이그레이션: 기존 테이블에 컬럼 추가 (이미 있으면 무시)
    from sqlalchemy import text

    for ddl in (
        "ALTER TABLE webhookevent ADD COLUMN headers_json VARCHAR DEFAULT ''",
        "ALTER TABLE pickuporder ADD COLUMN section_code VARCHAR DEFAULT ''",
        "ALTER TABLE pickuporder ADD COLUMN member_uid VARCHAR DEFAULT ''",
        "ALTER TABLE pickuporder ADD COLUMN member_grade VARCHAR DEFAULT ''",
    ):
        with Session(engine) as session:
            try:
                session.exec(text(ddl))
                session.commit()
            except Exception:
                pass

    with Session(engine) as session:
        # 지점 시드
        if not session.exec(select(Store)).first():
            for name in SEED_STORES:
                session.add(Store(name=name))
        # 재고: 지점×상품 조합 중 없는 것만 추가 (상품 개명·추가에도 부팅 시 정합)
        for store in SEED_STORES:
            for product in SEED_PRODUCTS:
                exists = session.exec(
                    select(InventoryItem).where(
                        InventoryItem.store_name == store,
                        InventoryItem.product_name == product,
                    )
                ).first()
                if exists is None:
                    session.add(
                        InventoryItem(store_name=store, product_name=product, qty=SEED_QTY)
                    )
        session.commit()


def get_session():
    with Session(get_engine()) as session:
        yield session
