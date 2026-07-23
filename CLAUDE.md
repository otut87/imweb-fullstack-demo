# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 아임웹 API 워크스페이스

아임웹(imweb) Open API 기반 백엔드·연동 프로젝트 모음. **프로젝트 하나당 `projects/<kebab-이름>/` 폴더 하나**(독립된 requirements/README/배포 구성), 아임웹 지식·스펙은 `docs/`에 공용 보관.

## 작업 전 필독 (docs/)

- [docs/imweb-integration-notes.md](docs/imweb-integration-notes.md) — **실연동으로 확정한 아임웹 지식 총정리.** OAuth(camelCase 파라미터·scope 규칙), API 공통 계약(봉투·unitCode·400 탐침 기법), 주문 도메인(sectionCode 주의·shipping-operation), 웹훅(심사 전 실이벤트 미발송 → 폴링 폴백), 상세페이지 DOM/JS 계약(SITE_SHOP_DETAIL)과 재렌더·FOUC 대응 패턴. **아임웹 관련 작업은 무조건 이 문서부터.**
- [docs/imweb-openapi-endpoints.md](docs/imweb-openapi-endpoints.md) — 전체 엔드포인트 인덱스(138개, Method+Path+요약)
- [docs/imweb-openapi-chunk.js](docs/imweb-openapi-chunk.js) — OpenAPI 3.1 풀스펙 번들(파라미터·스키마·에러코드). 엔드포인트 상세는 여기서 Grep

## 공통 명령

파이썬 venv는 워크스페이스 루트 `.venv` 공용(3.12). 프로젝트 폴더를 cwd로 실행한다(`.env`가 cwd 기준).

```powershell
# 테스트 (enchante-pickup 예)
cd C:\dev\enchante-erp\projects\enchante-pickup
..\..\.venv\Scripts\python smoke_test.py        # 22개 체크, 실API 호출은 env로 차단됨

# 로컬 서버
..\..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

새 프로젝트에 의존성 추가 시 루트 venv에 설치: `C:\dev\enchante-erp\.venv\Scripts\pip install -r requirements.txt`

## projects/enchante-pickup — 픽업 예약 ERP (운영 중)

풀스택 전문가 지원용 데모. 상세는 [projects/enchante-pickup/README.md](projects/enchante-pickup/README.md).

### 아키텍처 (요지)

```
Enchanté 쇼핑몰(support51251.imweb.me)
  ├─ sitecode/pickup-options.html  ← SEO>바디 삽입. 원본 옵션 숨기고 캘린더·시간·지점 UI로 교체,
  │                                   조작은 SITE_SHOP_DETAIL에 위임. /public/stock으로 지점 재고 표시
  └─ 주문 발생
       ├─ 웹훅(앱 심사 승인 후 활성) ─┐   둘 다 app/routers/webhooks.py의
       └─ 주문 API 폴링 30s(poller.py) ┴→ ingest_order_payload() 공용 파이프라인
            → 지점 라우팅·재고 차감 → SQLite → SSE(events.py) → ERP 대시보드(/erp)
ERP 상태 변경(픽업대기/픽업완료) → imweb/client.py shipping-operation PATCH → 아임웹 역반영
OAuth 토큰: imweb/oauth.py (DB 저장, 만료 5분 전 자동 갱신)
```

- 상태 7종: 결제대기→결제완료→상품준비→픽업대기→픽업완료 / 취소 / 반품 (`_map_status`가 아임웹 enum 매핑)
- 웹훅 수신은 원본(바디+헤더) 전량 `WebhookEvent`에 보존 후 deep-scan 파싱 — 스펙 확인·재처리용
- DB 스키마 변경은 `db.py init_db()`의 ALTER 시도 패턴(경량 마이그레이션)을 따른다

### 운영 서버 (AWS Lightsail)

- URL: `https://15.165.133.165.sslip.io` (/erp 대시보드, /healthz)
- SSH: `ssh -i projects\enchante-pickup\deploy\lightsail-default.pem ubuntu@15.165.133.165`
- 서버 배치는 `~/enchante-erp/` **플랫 구조**(이 프로젝트 폴더의 내용물). 배포는 로컬에서 tar 패키징:

```powershell
cd C:\dev\enchante-erp
tar -czf "$env:TEMP\enchante-erp.tgz" -C projects\enchante-pickup --exclude "*__pycache__*" app Dockerfile docker-compose.prod.yml Caddyfile requirements.txt README.md smoke_test.py sitecode
scp -i projects\enchante-pickup\deploy\lightsail-default.pem "$env:TEMP\enchante-erp.tgz" ubuntu@15.165.133.165:~/
ssh -i projects\enchante-pickup\deploy\lightsail-default.pem ubuntu@15.165.133.165 "tar -xzf enchante-erp.tgz -C enchante-erp && cd enchante-erp && sudo docker compose -f docker-compose.prod.yml up -d --build erp"
```

- `.env` 변경 시엔 `.env`도 scp 후 `--force-recreate erp`
- AWS CLI는 default 프로필(IAM `enchante-deploy`, Lightsail 전용 권한)
- 서버 DB 조회/스크립트: `sudo docker compose -f docker-compose.prod.yml exec -T erp python - < script.py` (따옴표 지옥 방지 — 인라인 -c 금지)

## projects/imweb-summary-helper — 크롬 익스텐션 '상품 요약설명 도우미'

관리자 상품 편집 화면(`/admin/shopping/product/detail`)의 요약 설명 입력을 돕는 MV3 확장. 상세는 [projects/imweb-summary-helper/README.md](projects/imweb-summary-helper/README.md).

- **툴바 팝업형(v2)** — 상시 콘텐츠 스크립트 없음. `activeTab`+`chrome.scripting.executeScript({world:'MAIN'})`으로 아이콘 클릭 시에만 접근해 페이지의 `FroalaEditor.INSTANCES`에서 인스턴스를 찾고, `html.set()` + `contentChanged` 트리거로 주입해야 아임웹 미리보기·저장과 연동된다 (요약설명 에디터 = Froala 3.1.1, `.fr-element` contenteditable). v1(인라인 패널 주입형)은 화면 점유 + 사이트 권한 메뉴 노출 문제로 팝업형 전환
- 관리자 DOM은 해시 클래스(`bo-shopping-product-…`)라 셀렉터 의존 금지 — **라벨 텍스트 앵커**("요약 설명"/"상품명"/"카테고리")로 탐색. 패널 삽입은 `.fr-box`의 실제 부모 기준 insertBefore (라벨의 부모 기준은 중첩 구조라 NotFoundError)
- 관리자 화면에서 JS `location.reload()` 호출은 차단됨. 카테고리 칩 텍스트에는 zero-width space가 섞여 있어 정제 필요

## 함정 요약 (전체 목록·근거는 integration-notes)

- OAuth·API 파라미터는 **camelCase** (`grantType`, `unitCode`, …)
- 섹션 API 주소는 `orderSectionNo`가 아니라 **`orderSectionCode`(os…)**, 경로는 `order-section`(단수)
- shipping-operation 허용 enum은 `SHIPPING_READY|SHIPPING|SHIPPING_COMPLETE` 3종뿐
- `isCancelReq`는 "취소 신청 **가능**" 플래그 — 취소 상태 아님
- **앱 심사 승인 전 웹훅 실이벤트 미발송** — 폴링 폴백을 끄지 말 것
- 인가 scope에 `site-info:write` 필수, 누락 시 30156
- 미문서 API는 빈 바디 400 응답이 필수 필드·enum을 알려줌 — 추측 대신 탐침
- 상세페이지 주입 UI는 아임웹 재렌더 영역 **밖**에 두고, 원본 참조는 클릭 시점 조회
- 배송 상태 전이는 **순차만 허용**(점프 400) + 택배 상품은 배송중 단계에 송장 필수 — `_push_shipping_status` 참고
- ⚠️ **PowerShell로 한글 JSON API 테스트 금지** — PS 5.1이 바디를 깨진 인코딩으로 보내 분기가 조용히 어긋남. 검증은 서버측 python 스크립트(`exec -T erp python - < script.py`)로
