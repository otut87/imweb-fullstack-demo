"""DB 모델 — 지점/주문 캐시/재고/웹훅 이벤트 로그/OAuth 토큰."""
from datetime import datetime

from sqlmodel import Field, SQLModel


class Store(SQLModel, table=True):
    """픽업 지점."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)  # 예: 강남점


class PickupOrder(SQLModel, table=True):
    """웹훅으로 수신한 주문의 로컬 캐시 (ERP 표시용)."""

    id: int | None = Field(default=None, primary_key=True)
    order_no: str = Field(index=True)  # 아임웹 주문번호
    section_code: str = ""  # orderSectionCode — 아임웹 상태 푸시(shipping-operation)에 필요
    event_type: str = ""  # 수신한 웹훅 이벤트명
    # 픽업 운영 상태: 결제대기/결제완료/상품준비/픽업대기/픽업완료/취소/반품
    status: str = "결제대기"
    store_name: str = Field(default="미지정", index=True)  # 옵션에서 추출한 픽업 지점
    pickup_date: str = ""  # 입력형 옵션에서 추출한 픽업 희망일
    customer_name: str = ""
    member_uid: str = ""  # 아임웹 회원 UID (이메일) — 회원 API 연동 키
    member_grade: str = ""  # 회원 쇼핑 등급명 (Member-Info API로 보강)
    items_summary: str = ""  # "Radiant Glow Serum x2 외 1건"
    amount: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class InventoryItem(SQLModel, table=True):
    """지점별 재고."""

    id: int | None = Field(default=None, primary_key=True)
    store_name: str = Field(index=True)
    product_name: str = Field(index=True)
    qty: int = 0


class WebhookEvent(SQLModel, table=True):
    """수신한 웹훅 원본 로그 — 페이로드 스펙 확인/디버깅/재처리용."""

    id: int | None = Field(default=None, primary_key=True)
    event_type: str = ""
    raw_body: str = ""  # JSON 원문 그대로 보존
    headers_json: str = ""  # 수신 헤더 전체 (아임웹 인증정보 전달 방식 확인용)
    received_at: datetime = Field(default_factory=datetime.now)


class OAuthToken(SQLModel, table=True):
    """사이트별 액세스/리프레시 토큰 저장.

    아임웹 토큰 수명: access 2시간 / refresh 90일 (문서 기준).
    """

    id: int | None = Field(default=None, primary_key=True)
    site_code: str = Field(index=True, unique=True)
    access_token: str = ""
    refresh_token: str = ""
    scope: str = ""
    expires_at: datetime = Field(default_factory=datetime.now)  # access 만료 시각
    updated_at: datetime = Field(default_factory=datetime.now)
