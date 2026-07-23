# AWS Lightsail 배포 가이드

목표: `https://<도메인>` 에서 웹훅 수신 + ERP 대시보드 상시 운영.

## 1. 인스턴스 생성 (AWS 콘솔 — 5분)

1. [Lightsail 콘솔](https://lightsail.aws.amazon.com/) → **인스턴스 생성**
2. 리전 **서울(ap-northeast-2)**, 플랫폼 **Linux**, 블루프린트 **OS 전용 → Ubuntu 24.04**
3. 플랜: **1GB RAM** 권장(도커 빌드 여유). 512MB는 빌드 시 스왑 필요할 수 있음
4. 생성 후 **네트워킹 탭 → 고정 IP 생성·연결**
5. 같은 탭 방화벽에 규칙 추가: **HTTP(80)**, **HTTPS(443)** (SSH 22는 기본)

## 2. 도메인 결정

- **보유 도메인 있으면**: `erp.<도메인>` A 레코드 → 고정 IP. `.env`의 `DOMAIN=erp.<도메인>`
- **없으면**: `DOMAIN=<고정IP>.sslip.io` (예: `3.35.10.20.sslip.io`) — 별도 설정 없이
  Caddy가 Let's Encrypt 인증서 자동 발급. 데모 URL로 충분

## 3. 서버 셋업 (SSH — 5분)

```bash
# Lightsail 브라우저 SSH 또는 로컬에서 ssh ubuntu@<고정IP>
curl -fsSL <이 저장소 raw URL>/deploy/setup-server.sh | bash
# 또는 파일 복사 후: bash setup-server.sh
```

재접속 후(도커 그룹 반영). compose·.env.example은 모노레포의
`projects/enchante-pickup/` 하위에 있으므로 그 경로로 이동한다:

```bash
git clone <저장소URL> enchante-erp && cd enchante-erp/projects/enchante-pickup
cp .env.example .env && nano .env
# IMWEB_CLIENT_ID / SECRET / SITE_CODE / UNIT_CODE / SCOPE 입력
# IMWEB_REDIRECT_URI=https://<도메인>/auth/callback  ← https, 실제 도메인으로!
# WEBHOOK_SHARED_SECRET=<임의의 긴 문자열>
# DOMAIN=<도메인>
docker compose -f docker-compose.prod.yml up -d --build
```

> 로컬(Windows)에서 개발 중이라면 git clone 대신 tar 업로드로 배포한다 —
> 정확한 명령은 워크스페이스 루트 `CLAUDE.md`의 배포 절차를 따른다.

확인: `https://<도메인>/healthz` → `{"ok":true}`

## 4. 아임웹 개발자센터 연결

1. **앱 정보 → 리다이렉트 URI에 추가**: `https://<도메인>/auth/callback`
   (로컬 `http://localhost:8000/auth/callback`도 개발용으로 유지 가능 — "+ 추가")
2. **웹훅 등록**: 주문 생성/입금완료/취소 등 →
   `https://<도메인>/webhooks/imweb?secret=<WEBHOOK_SHARED_SECRET>`
3. 개발자센터 **테스트 보내기** → 서버 `docker compose logs -f erp`로 수신 확인
4. 브라우저에서 `https://<도메인>/auth/login` 1회 → 토큰 발급 → `/erp` 대시보드

## 5. 업데이트 배포

```bash
cd enchante-erp && git pull
cd projects/enchante-pickup
docker compose -f docker-compose.prod.yml up -d --build
```

> 실제 이 데모는 로컬 tar 패키징 → scp → 원격 재빌드로 배포한다(서버는 홈에 플랫 배치).
> 재현 가능한 정확한 명령은 워크스페이스 루트 `CLAUDE.md` 참고.

## 트러블슈팅

- **인증서 발급 실패**: 80/443 방화벽 확인, `DOMAIN`이 고정 IP를 가리키는지 확인 후
  `docker compose -f docker-compose.prod.yml restart caddy`
- **웹훅 403**: 등록한 URL의 `secret` 쿼리와 `.env`의 `WEBHOOK_SHARED_SECRET` 일치 확인
- **로그 확인**: `docker compose -f docker-compose.prod.yml logs -f --tail 100`
