"""앱 설정 — .env에서 로드."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": .env에는 compose 전용 변수(DOMAIN 등)도 있어 낯선 키는 무시
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 아임웹 OAuth 앱 정보 (개발자센터에서 발급)
    imweb_client_id: str = ""
    imweb_client_secret: str = ""
    imweb_site_code: str = ""
    imweb_unit_code: str = ""  # /site-info의 unitList[].unitCode — 주문/상품 조회 필수
    imweb_redirect_uri: str = "http://localhost:8000/auth/callback"
    # 실검증 확정 scope (site-info:write=인가 필수, order:write=상태 푸시, payment:write=입금확인,
    # member-info:read=회원 등급). 형식은 카테고리:read|write.
    imweb_scope: str = (
        "site-info:write order:read order:write product:read payment:write member-info:read"
    )

    # 아임웹 Open API 엔드포인트 (developers-docs.imweb.me 기준)
    imweb_oauth_base: str = "https://openapi.imweb.me"
    imweb_api_base: str = "https://openapi.imweb.me"

    # 주문 API 폴링 폴백 (앱 심사 승인 전엔 웹훅 실이벤트가 오지 않음)
    imweb_poll_enabled: bool = True
    imweb_poll_interval: int = 30  # 초
    # ERP 상태 변경 → 아임웹 역방향 푸시(shipping-operation)
    imweb_push_enabled: bool = True

    # 카카오 '나에게 보내기' 운영 알림 (신규 픽업 주문 → 담당자 카톡)
    kakao_rest_api_key: str = ""
    kakao_redirect_uri: str = ""

    # 크롬 확장 '요약설명 도우미' AI 프록시용 — 키는 서버 .env에만 존재(확장/저장소에 미포함)
    anthropic_api_key: str = ""

    # 웹훅 수신 검증용 공유 시크릿 (URL 쿼리)
    webhook_shared_secret: str = "change-me"
    # 아임웹이 이벤트와 함께 전달하는 인증정보 (개발자센터 웹훅 화면의 값).
    # 실측: authorization 헤더로 전달됨 → webhooks.py에서 검증.
    imweb_webhook_auth: str = ""

    db_path: str = "enchante_erp.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
