"""아임웹 Open API 클라이언트 — Bearer 인증 + 401 시 자동 토큰 갱신.

확정 스펙 (2026-07-23 실호출 검증):
- Base: https://openapi.imweb.me
- GET /site-info                    → data.unitList[].unitCode
- GET /orders?page&limit&unitCode   → data.{totalCount,totalPage,currentPage,pageSize,list[]}
- GET /products?page&limit&unitCode → 동일 페이지네이션 봉투
- 응답 봉투: {"statusCode":200,"data":{...}} / 오류: {"statusCode":4xx,"error":{errorCode,message,data}}
- limit 범위 1~100, 필드 네이밍 camelCase

주문 데이터 구조 (문서: 주문 이해하기): Order > OrderSection > OrderSectionItem
TODO(확인): 주문 단건 조회 경로(/orders/{orderNo} 추정) — 실주문 생기면 검증
"""
import httpx
from sqlmodel import Session, select

from ..config import get_settings
from ..models import OAuthToken
from .oauth import get_valid_access_token, refresh_token, save_tokens


class ImwebClient:
    def __init__(self, session: Session) -> None:
        self._db = session
        self._settings = get_settings()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {get_valid_access_token(self._db)}"}

    def request(self, method: str, path: str, **kwargs) -> dict:
        """공통 요청 — 401이면 강제 갱신 후 1회 재시도, 응답 봉투(data) 언랩."""
        url = f"{self._settings.imweb_api_base}{path}"
        with httpx.Client(timeout=15) as client:
            response = client.request(method, url, headers=self._headers(), **kwargs)
            if response.status_code == 401:
                row = self._db.exec(
                    select(OAuthToken).where(
                        OAuthToken.site_code == self._settings.imweb_site_code
                    )
                ).first()
                if row:
                    save_tokens(self._db, refresh_token(row.refresh_token))
                response = client.request(method, url, headers=self._headers(), **kwargs)
            response.raise_for_status()
            body = response.json()
            return body.get("data", body)

    # --- 편의 메서드 -------------------------------------------------------

    def get_site_info(self) -> dict:
        return self.request("GET", "/site-info")

    def list_orders(self, page: int = 1, limit: int = 50, **params) -> dict:
        params.update(page=page, limit=limit, unitCode=self._settings.imweb_unit_code)
        return self.request("GET", "/orders", params=params)

    def list_products(self, page: int = 1, limit: int = 50, **params) -> dict:
        params.update(page=page, limit=limit, unitCode=self._settings.imweb_unit_code)
        return self.request("GET", "/products", params=params)

    def get_member(self, member_uid: str) -> dict:
        """회원 조회 — scope member-info:read, unitCode 필수(실측).

        주의: 운영진(관리자) 계정은 회원이 아니라 404(30001) — 별도 /member-info/admin 리소스.
        """
        return self.request(
            "GET",
            f"/member-info/members/{member_uid}",
            params={"unitCode": self._settings.imweb_unit_code},
        )

    def get_order(self, order_no: str) -> dict:
        # 실검증(2026-07-23): GET /orders/{orderNo} 200 확인
        return self.request("GET", f"/orders/{order_no}")

    def confirm_bank_transfer(self, order_no: str) -> dict:
        """무통장 입금 수동 확인 처리 — ERP '결제완료' 전환 시 아임웹 반영.

        스펙: PATCH /payments/{orderNo}/bank-transfer/confirm (scope: payment:write)
        에러 30061 = 결제 정보 없음(이미 처리됐거나 무통장 아님).
        """
        return self.request(
            "PATCH",
            f"/payments/{order_no}/bank-transfer/confirm",
            json={"unitCode": self._settings.imweb_unit_code},
        )

    def set_section_shipping_status(
        self, order_no: str, section_code: str, status: str
    ) -> dict:
        """섹션 배송 상태 전이 — ERP→아임웹 역방향 동기화.

        실검증(2026-07-23): PATCH .../shipping-operation 200 확인.
        허용 enum: SHIPPING_READY | SHIPPING | SHIPPING_COMPLETE (API 검증 메시지 기준)
        """
        return self.request(
            "PATCH",
            f"/orders/{order_no}/order-section/{section_code}/shipping-operation",
            json={
                "unitCode": self._settings.imweb_unit_code,
                "orderSectionStatus": status,
            },
        )
