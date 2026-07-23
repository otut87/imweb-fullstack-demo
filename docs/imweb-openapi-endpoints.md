# 아임웹 OpenAPI 엔드포인트 인덱스

> 원본: developers-docs.imweb.me/reference 의 OpenAPI 3.1.0 스펙 번들
> (`imweb-openapi-chunk.js` — 전체 파라미터/스키마는 이 파일에서 검색)
> Base URL: `https://openapi.imweb.me` / 인증: `Authorization: Bearer {accessToken}`

| Method | Path | Summary |
|---|---|---|
| GET | `/community/forms` |  |
| GET | `/community/forms/{formNo}` | 입력폼 상세 조회 |
| GET | `/community/form-submissions` |  |
| GET | `/community/form-submissions/{submitCode}` | 입력폼 제출 상세 조회 |
| GET | `/community/qna` |  |
| POST | `/community/qna` | Q&A 답변 등록 |
| GET | `/community/qna-answer` | Q&A 답글 목록 조회 |
| GET | `/community/qna/{qnaNo}` | Q&A 조회 |
| POST | `/community/review` | 구매평 작성 |
| GET | `/community/review` |  |
| PUT | `/community/review/{reviewNo}` | 구매평 수정 |
| DELETE | `/community/review/{reviewNo}` | 구매평 삭제 |
| GET | `/community/review/{reviewNo}` | 구매평 조회 |
| POST | `/community/review-answer` | 구매평 답글 등록 |
| GET | `/community/review-answer` | 구매평 답글 목록 조회 |
| DELETE | `/community/review-answer/{reviewAnswerNo}` | 구매평 답글 삭제 |
| GET | `/community/review/cursor` |  |
| GET | `/member-info/members` | GTE 날짜 검색 예시 |
| GET | `/member-info/members/cursor` | GTE 날짜 검색 예시 |
| GET | `/member-info/members/product/wish-list` |  |
| GET | `/member-info/members/product/carts` |  |
| GET | `/member-info/members/{memberUid}` | 회원 조회 |
| GET | `/member-info/groups` | 회원 그룹 목록 조회 |
| GET | `/member-info/groups/{memberGroupCode}/members` |  |
| GET | `/member-info/grades` | 회원 쇼핑 등급 목록 조회 |
| GET | `/member-info/grades/members` |  |
| GET | `/member-info/admin/groups` | 운영진 그룹 목록 조회 |
| GET | `/member-info/admin/groups/{siteGroupCode}/members` |  |
| GET | `/member-info/admin/{adminUid}` | 운영진 조회 |
| PATCH | `/member-info/members/{memberUid}/agree-info` | 회원 동의 정보 수정 |
| PUT | `/member-info/members/{memberUid}/groups` | 회원 그룹 변경 |
| PUT | `/member-info/members/groups/bulk` | 회원 그룹 일괄 변경 |
| PUT | `/member-info/members/{memberUid}/grade` | 회원 등급 변경 |
| PUT | `/member-info/members/grades/bulk` |  |
| GET | `/member-info/members/{memberUid}/wish-list` | 회원 위시리스트 조회 |
| GET | `/member-info/members/{memberUid}/carts` | 회원 장바구니 목록 조회 |
| GET | `/oauth2/authorize` |  |
| POST | `/oauth2/token` |  |
| GET | `/orders/parcel-company-list` | 택배사 목록 조회 |
| GET | `/orders/shipping-places` |  |
| GET | `/orders` |  |
| GET | `/orders/{orderNo}` | 주문 조회 |
| GET | `/orders/{orderNo}/order-sections` |  |
| GET | `/orders/{orderNo}/order-section/{orderSectionCode}` | 주문 섹션 조회 |
| GET | `/orders/{orderNo}/order-section/{orderSectionCode}/order-section-items` | 주문 섹션아이템 목록 조회 |
| GET | `/orders/{orderNo}/order-section/{orderSectionCode}/order-section-item/{orderSectionItemNo}` |  |
| GET | `/orders/{orderNo}/coupons` | 주문 쿠폰 목록 조회 |
| PATCH | `/orders/{orderNo}/shipping-operation` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/shipping-operation` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/shipping-operation` |  |
| POST | `/orders/{orderNo}/invoice` |  |
| PATCH | `/orders/{orderNo}/invoice` |  |
| DELETE | `/orders/{orderNo}/invoice` |  |
| POST | `/orders/{orderNo}/order-section/{orderSectionCode}/invoice` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/invoice` |  |
| DELETE | `/orders/{orderNo}/order-section/{orderSectionCode}/invoice` |  |
| POST | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/invoice` |  |
| PATCH | `/orders/{orderNo}/cancel-request` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/cancel-request` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/cancel-request` |  |
| PATCH | `/orders/{orderNo}/cancel-reject` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/cancel-reject` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/cancel-reject` |  |
| PATCH | `/orders/{orderNo}/return-request` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/return-request` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/return-request` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/retrieve-complete` |  |
| PATCH | `/orders/{orderNo}/return-reject` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/return-reject` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/return-reject` |  |
| PATCH | `/orders/{orderNo}/exchange-request` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/exchange-request` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/exchange-request` |  |
| PATCH | `/orders/{orderNo}/exchange-reject` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/exchange-reject` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/exchange-reject` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/cancel-approve` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/cancel-approve` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/return-approve` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/return-approve` |  |
| PATCH | `/orders/{orderNo}/order-section/{orderSectionCode}/exchange-approve` |  |
| PATCH | `/orders/{orderNo}/order-section-items/{orderSectionItemNo}/exchange-approve` |  |
| PATCH | `/payments/{orderNo}/bank-transfer/confirm` | 주문 무통장 입금 수동 확인 처리 |
| POST | `/products` | bracket notation |
| GET | `/products` |  |
| GET | `/products/shop-categories` | 상품 카테고리 목록 조회 |
| GET | `/products/shop-showcases` | 상품 기획전 목록 조회 |
| GET | `/products/shop-naver-categories` | 상품 네이버 카테고리 목록 조회 |
| PATCH | `/products/status` | 상품 상태 일괄 수정 |
| GET | `/products/{prodNo}/options` |  |
| GET | `/products/{prodNo}/options/{optionCode}` |  |
| PATCH | `/products/{prodNo}/options/{optionCode}` |  |
| GET | `/products/options` | 상품 옵션 일괄 조회 |
| GET | `/products/{prodNo}` | 상품 조회 |
| PATCH | `/products/{prodNo}` |  |
| GET | `/products/{prodNo}/option-details` |  |
| GET | `/products/{prodNo}/option-details/{optionDetailCode}` |  |
| PATCH | `/products/{prodNo}/option-details/{optionDetailCode}` |  |
| GET | `/products/{prodNo}/shipping-service-settings` | 상품 빠른 배송 설정 조회 |
| PATCH | `/products/{prodNo}/relative-info` | 상품 연관 상품 정보 수정 |
| PATCH | `/products/{prodNo}/seo` | 상품 SEO 정보 수정 |
| GET | `/products/{prodNo}/shipping-settings` |  |
| PATCH | `/products/{prodNo}/shipping-settings` |  |
| PATCH | `/products/{prodNo}/stock-info` | 상품 재고 수정 |
| PATCH | `/products/{prodNo}/price` | 상품 가격 설정 수정 |
| PATCH | `/products/{prodNo}/discount-info` | 상품 할인 설정 수정 |
| PATCH | `/products/{prodNo}/display` | 상품 외부 노출 설정 수정 |
| PATCH | `/products/{prodNo}/classification` | 상품 분류 정보 수정 |
| PATCH | `/products/{prodNo}/status` | 상품 상태 수정 |
| PATCH | `/products/{prodNo}/external-integration-info` | 상품 외부 연동정보 수정 |
| PATCH | `/products/{prodNo}/additional-info` | 상품 추가 상품 정보 수정 |
| PATCH | `/products/{prodNo}/etc-info` | 상품 기타 설정 수정 |
| PATCH | `/products/{prodNo}/exhibitions` | 상품 진열 설정 수정 |
| POST | `/products/{prodNo}/images` |  |
| GET | `/promotion/shop-point` |  |
| GET | `/promotion/shop-point-log` |  |
| PUT | `/promotion/shop-point/change/member/{memberUid}` |  |
| PUT | `/promotion/shop-point/change/type` |  |
| GET | `/promotion/shop-coupon/{shopCouponCode}` | 쿠폰 조회 |
| POST | `/promotion/shop-coupon` |  |
| GET | `/promotion/shop-coupon` |  |
| POST | `/promotion/shop-coupon/{couponCode}/issue` |  |
| POST | `/promotion/shop-coupon/{couponCode}/issue/bulk` |  |
| POST | `/promotion/shop-coupon/{couponCode}/issue/group` |  |
| GET | `/promotion/shop-coupon/{shopCouponCode}/coupon-issue` |  |
| GET | `/promotion/shop-coupon/{shopCouponCode}/coupon-issue-target` |  |
| GET | `/promotion/shop-coupon/member/{memberUid}/coupon-issue-target` |  |
| GET | `/promotion/shop-coupon/member/{memberUid}/coupon-issue` |  |
| GET | `/script` |  |
| POST | `/script` | 스크립트 등록 |
| PUT | `/script` | 스크립트 수정 |
| DELETE | `/script` |  |
| GET | `/site-info` | 사이트 정보 조회 |
| GET | `/site-info/menu` | 사이트 메뉴 목록 조회 |
| GET | `/site-info/unit/{unitCode}` | 유닛 정보 조회 |
| PATCH | `/site-info/integration-complete` | 연동완료 처리 |
| PATCH | `/site-info/integration-cancellation` | 연동해제 처리 |
| PATCH | `/site-info/integration-info` | 연동정보 수정 |
