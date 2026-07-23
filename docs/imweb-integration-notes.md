# 아임웹 연동 실전 노트 (실연동으로 확정한 지식)

> 2026-07-23, Enchanté 픽업 ERP 데모(projects/enchante-pickup) 구축 과정에서
> **실호출·실이벤트로 검증**한 내용만 기록. 추정은 (추정)으로 표기.
> 엔드포인트 상세 스펙은 [imweb-openapi-endpoints.md](imweb-openapi-endpoints.md)(인덱스)와
> [imweb-openapi-chunk.js](imweb-openapi-chunk.js)(풀스펙·스키마·에러코드)에서 검색.

## 1. 연동 준비 (개발자센터)

- 앱 생성 → 클라이언트 ID/시크릿 자동 발급. **리다이렉트 URI는 정확히 일치**해야 함(복수 등록 가능).
- **API 설정에서 카테고리 활성화**가 선행 조건 (웹훅 등록도 해당 scope 활성화 필요).
- **연동 사이트 관리 → 테스트연동**: 자기 사이트를 앱에 연결. **테스트연동 상태로 전 API 사용 가능**
  (연동완료처리·심사 불필요). 사이트 코드는 이 화면에서 확인.
- 에러 코드: `30132` = 사이트-앱 미연동, `30156` = 인가 scope에 `site-info:write` 누락.
- **unitCode**: 사이트 하위 유닛 단위. `GET /site-info` 응답의 `unitList[].unitCode`.
  주문/상품 등 대부분의 조회에 필수 파라미터.

## 2. OAuth 2.0

| 항목 | 값 |
|---|---|
| 인가 | `GET https://openapi.imweb.me/oauth2/authorize` |
| 토큰 발급/갱신 | `POST https://openapi.imweb.me/oauth2/token` (JSON 본문 OK) |
| 파라미터 | **camelCase** — `responseType` `clientId` `redirectUri` `scope` `siteCode` `state` / `grantType` `clientSecret` `refreshToken` (표준 OAuth의 snake_case 아님!) |
| 토큰 수명 | Access **2시간** / Refresh **90일** — 갱신 시 둘 다 재발급 |
| scope 형식 | `카테고리:read\|write` (예: `order:read order:write product:read`). **인가 요청에 `site-info:write` 필수** |
| Rate limit | 버킷 25, 초당 2 회복. `X-RateLimit-*` 헤더 |

구현 참고: `projects/enchante-pickup/app/imweb/oauth.py` (만료 5분 전 선제 갱신, 응답 래핑 유연 파싱).

## 3. API 공통 계약

- Base `https://openapi.imweb.me`, 인증 `Authorization: Bearer {accessToken}`.
- 응답 봉투: 성공 `{"statusCode":200,"data":{...}}` / 오류 `{"statusCode":4xx,"error":{"errorCode","message","data":[검증상세]}}`.
- 목록 조회: `page`(≥1)+`limit`(1~100)+`unitCode` 필수 → `data.{totalCount,totalPage,currentPage,pageSize,list[]}`.
- 필드 네이밍 camelCase.
- **미문서 API 탐침 기법**: 후보 경로에 빈 바디로 요청하면 400 검증 에러가
  **필수 필드·허용 enum까지 알려줌** (405 아님 → 메서드도 이걸로 판별). 404 `Cannot {METHOD} {path}` = 경로 오답.

## 4. 주문 도메인

- 구조: **Order > OrderSection(배송상태 그룹) > OrderSectionItem**.
- 조회: `GET /orders?page&limit&unitCode`, `GET /orders/{orderNo}` (orderNo는 **숫자**).
- 섹션 리소스 주소는 **`orderSectionCode`(os2026...)** 사용 — `orderSectionNo`(주문번호-S1)가 아님! 경로도
  `order-section`(단수) : `/orders/{orderNo}/order-section/{orderSectionCode}/...`
- **상태 전이**: `PATCH .../order-section/{code}/shipping-operation`
  본문 `{"unitCode","orderSectionStatus"}` — 허용 enum **`SHIPPING_READY | SHIPPING | SHIPPING_COMPLETE`** 뿐.
- ⚠️ **배송 전이는 순차만 허용** (READY→COMPLETE 점프 불가, 단계 건너뛰면 400):
  에러표 실측 — `30063 결제 완료 주문만 배송처리` / `30077 배송준비 변경 불가` / `30084 배송중 변경 불가` /
  `30090 배송대기 상태만 가능` / **`30065·30085 배송중 처리엔 송장 필요`** / `30095 송장 미등록 섹션`.
  → 목표 상태까지 현재 상태를 조회해 **단계별로 반복 호출**해야 함 (구현: enchante-pickup `_push_shipping_status`).
  → **택배(PARCEL) 상품은 배송중 단계에 송장이 필수** — 픽업 시나리오면 상품 배송방식을
  '방문수령'으로 설정해 송장 규칙을 피하는 것을 권장.
  상품준비 진입은 API로 불가(입금확인 등 아임웹 쪽 프로세스), 취소/반품/교환은 별도
  `cancel-request/-approve/-reject`, `return-*`, `exchange-*` 플로우 (인덱스 참고).
- 상태 enum 예: `PAYMENT_WAIT`(추정) `PRODUCT_PREPARATION` `SHIPPING_READY` `SHIPPING` `SHIPPING_COMPLETE`
  `EXCHANGE_SHIPPING_*` — 대문자 스네이크.
- **`isCancelReq`는 "취소 신청 가능 여부"** — 취소된 상태가 아님 (상품준비 주문도 "Y").
- **결제(입금) 상태는 `payments[].paymentStatus`**: `PAYMENT_PREPARATION`(무통장 입금 전) →
  `PAYMENT_COMPLETE`(+`paymentCompleteTime`). ⚠️ 섹션 상태는 **입금 전에도 PRODUCT_PREPARATION**이므로
  주문 단계 판정에 섹션만 쓰면 미입금 주문을 오분류함. `totalPaymentPrice`도 미입금 시 0.
- **무통장 입금 확인을 API로 처리 가능**: `PATCH /payments/{orderNo}/bank-transfer/confirm`
  (scope **`payment:write`** 필요, 30061=결제 정보 없음/이미 처리). scope 추가 시 재인가 필요.
- 관리자 탭과의 대응: 결제대기(미입금) / 상품준비중(입금완료+PREPARATION) / 배송대기(SHIPPING_READY) /
  배송중(SHIPPING) / 배송완료(SHIPPING_COMPLETE).
- **폴링·웹훅 동기화 시 랭크 가드 패턴**: 상태에 진행 순서 랭크를 부여하고 원격 매핑이 현재보다
  낮으면 무시(취소·반품은 예외로 즉시 적용) — 운영자가 ERP에서 수동 진행한 상태를 폴링이
  되돌리는 진동을 방지. (구현: enchante-pickup `webhooks.py` STATUS_RANK)
- 옵션: `sectionItems[].productInfo.optionInfo` = **`{"옵션명":"값"}` 평면 dict**
  (`optionInfoList`도 병행 제공). 수량 `qty`는 sectionItem 레벨.
- 주문자: `ordererName/ordererEmail/ordererCall`, 금액: `totalPaymentPrice`(결제액) 외 다수.

## 4.5 회원 (Member-Info)

- `GET /member-info/members/{memberUid}` — **unitCode 쿼리 필수**(실측). memberUid = 이메일.
- ⚠️ **운영진(관리자) 계정은 '회원'이 아님** — 관리자 주문의 memberUid로 회원 조회하면
  404(30001 "존재하지 않는 회원"). 운영진은 별도 리소스 `/member-info/admin/{adminUid}`.
  (샘플사이트 테스트 주문은 대부분 관리자 주문이라 이 케이스에 걸림)
- 등급 목록 `GET /member-info/grades?page&limit&unitCode`.

## 5. 웹훅

- 개발자센터 웹훅 메뉴에서 **이벤트별 URL 1개** 등록 (한 URL에 여러 이벤트는 OK). 주문 계열 30개 내외.
- ⚠️ **앱 심사 승인 전엔 실이벤트 미발송** — '테스트 보내기'만 동작
  (웹훅 화면 문구: "API 승인 후 사이트에서 발생하는 이벤트가 전송").
  → **주문 목록 폴링 폴백 필수** (`app/poller.py`, upsert 기반이라 승인 후 웹훅과 중복 없이 공존).
- 페이로드: `{"eventType":"ORDER_*","eventTime":ms,"data":{orderNo, section:{...sectionItems...}, beforeSection}}`.
- **인증**: 요청 `authorization` 헤더에 개발자센터 '인증 정보' 값이 **그대로**(Bearer 접두사 없이) 옴.
  User-Agent `axios/…`. 수신부는 이 값 검증 + (자체 secret 쿼리 병행 권장).
- 수신부 설계: 원본(바디+헤더) 전량 DB 보존 → 유연 파서(deep-scan) → 도메인 반영. 스펙 변화에 강함.

## 6. 프론트 커스터마이징 (상품 상세, 사이트 코드 주입)

설치 위치: 관리자 > 환경설정 > SEO > **바디(body) 삽입 코드**. (사이트 코드는 위젯 스튜디오
제약 — !important 금지 등 — 을 받지 않음)

### 아임웹 상세페이지 DOM/JS 계약 (실측)
- 옵션 영역 `#prod_options` (.goods_select), 부모 `#goods_wrap` — PC/모바일 레이아웃 간 **이동**됨.
- 입력형 옵션: `input._requireInputOption` — 값 설정 후 `change` 이벤트를 쏘면
  inline `onchange`의 `SITE_SHOP_DETAIL.changeRequireInputOption(...)`이 등록 처리.
- 기본형 옵션: `._form_select_wrap` 드롭다운, 각 항목 `<a>`의 onclick이
  `SITE_SHOP_DETAIL.selectRequireOption(...)` — **원본 `<a>`를 대리 클릭**하면 옵션코드·가격 무손상.
- 선택 결과: `#prod_selected_options` 안 `._selected_require_option` 행 —
  `SITE_SHOP_DETAIL.removeSelectedOption(i,'prod')`, `increaseOptionCount/decreaseOptionCount(i,'prod')`,
  수량 `input._count`, 총액 `.total_price`.
- **다른 옵션 조합을 선택하면 행이 추가**됨(장바구니식) — 단일 선택 UX가 필요하면 기존 행을
  제거(removeSelectedOption 반복) 후 재등록.

### 재렌더·FOUC 대응 패턴 (v3에서 확립)
1. 원본 영역은 **CSS로 로드 즉시 숨김** (`#prod_options, #prod_selected_options {display:none}`) → FOUC 제거.
2. 커스텀 패널은 **아임웹 재렌더 영역 밖**(#goods_wrap 형제)에 1회 생성 → 옵션 변경 시 파괴되지 않음(렉·깜빡임 제거).
3. 모든 조작은 **클릭 시점에 현재 DOM을 조회**해 원본에 위임 (참조 보관 금지 — 재렌더로 stale 됨).
4. 주기 tick(400ms)으로 패널 위치(레이아웃 이동)·미러(수량/총액)만 갱신.
5. 대상 옵션이 없는 상품은 타임아웃 후 원본 복원 (다른 상품 페이지 안전).

구현체: `projects/enchante-pickup/sitecode/pickup-options.html` (인라인 캘린더·시간 슬롯·지점 버튼·재고 표시).

## 6.5 외부 API — 카카오 '나에게 보내기' (운영 알림)

- 인가/토큰: `kauth.kakao.com/oauth/authorize|token` — **form-urlencoded**, scope `talk_message`.
  access ~6시간 / refresh ~2개월 (갱신 응답에 refresh_token 없으면 기존 유지).
- 발송: `POST kapi.kakao.com/v2/api/talk/memo/default/send`, `template_object`(JSON 문자열) form 필드.
  수신 대상은 **연결한 본인 계정의 '나와의 채팅'뿐** — 고객 발송은 알림톡(사업자 채널+템플릿 심사) 필요.
- 구현 패턴: 아임웹 OAuth와 동일한 토큰 저장·선제 갱신 구조 재사용 (enchante-pickup `app/kakao.py`).

## 7. 인프라 패턴 (데모 검증)

- FastAPI + SQLite + SSE 단일 컨테이너, Caddy 리버스 프록시(80/443, Let's Encrypt 자동).
- 도메인 없이 `<고정IP>.sslip.io`로 TLS 발급 성공 (Lightsail).
- 웹훅+폴링 이중화, ERP→아임웹 역푸시(shipping-operation), 쇼핑몰 페이지용 공개 API는
  CORS를 해당 사이트 오리진에만 GET 허용.

## 8. 기타

- 개발자 문서: https://developers-docs.imweb.me (가이드), Reference는 Scalar SPA —
  풀스펙은 assets의 openapiMap이 가리키는 청크 JS에 번들됨 (docs/imweb-openapi-chunk.js로 보관).
- 샘플사이트(전문가 등록 계정)는 플랜 제약 없이 전 기능 사용 가능.
- 웹훅/OAuth 콜백 URL 변경 시 개발자센터 등록값도 같이 갱신할 것.
