"""로컬 스모크 테스트 — 아임웹 없이 전체 루프 검증.

페이로드는 2026-07-23 웹훅 '테스트 보내기'로 확인한 실스펙 구조를 따른다:
eventType / data.section.sectionItems[].productInfo.optionInfo(평면 dict) / authorization 헤더.
"""
import json
import os
import sys

# 한국어 Windows 콘솔(cp949)에서 결과 출력이 UnicodeEncodeError로 죽지 않게 UTF-8 강제
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

os.environ["DB_PATH"] = "smoke_test.db"
os.environ["IMWEB_WEBHOOK_AUTH"] = "test-auth"  # .env 값 대신 테스트용 (env가 .env보다 우선)
os.environ["WEBHOOK_SHARED_SECRET"] = "change-me"
os.environ["IMWEB_POLL_ENABLED"] = "0"  # 테스트 중 실API 폴링 방지
os.environ["IMWEB_PUSH_ENABLED"] = "0"  # 테스트 중 실API 상태 푸시 방지
if os.path.exists("smoke_test.db"):
    os.remove("smoke_test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

REAL_SPEC_WEBHOOK = {
    "eventType": "ORDER_CREATE",
    "eventTime": 1784799827734,
    "data": {
        "siteCode": "S2024042224f6a873eadf8",
        "unitCode": "u202404226625acd43ff14",
        "orderNo": 20260723000001,
        "saleChannel": "IMWEB",
        "orderType": "SHOPPING",
        "ordererName": "홍길동",
        "memberUid": "hong@test.kr",
        "paymentAmount": 144000,
        "section": {
            "orderSectionNo": "20260723000001-S1",
            "orderSectionCode": "os20260723smoke",
            "orderSectionStatus": "PAYMENT_WAIT",
            "sectionItems": [
                {
                    "orderSectionItemNo": "oi-test-1",
                    "qty": 2,
                    "isPromotion": "N",
                    "productInfo": {
                        "prodNo": 1,
                        "prodName": "Radiant Glow Serum I",
                        "optionInfo": {"지점선택": "강남점", "픽업 희망일": "2026-07-26 14:00"},
                    },
                }
            ],
        },
    },
}

AUTH = {"Authorization": "test-auth"}

with TestClient(app) as client:
    checks = []

    r = client.get("/healthz")
    checks.append(("healthz", r.status_code == 200))

    r = client.get("/erp")
    checks.append(("erp 대시보드 HTML", r.status_code == 200 and "Enchanté" in r.text))

    r = client.get("/erp/api/stores")
    checks.append(("지점 시드 3곳", r.json() == ["강남점", "성수점", "천안점"]))

    r = client.post(
        "/webhooks/imweb?secret=change-me",
        content=json.dumps(REAL_SPEC_WEBHOOK),
        headers=AUTH,
    )
    checks.append(("실스펙 웹훅 수신 + 지점 라우팅", r.status_code == 200 and r.json().get("store") == "강남점"))

    r = client.post("/webhooks/imweb?secret=wrong", headers=AUTH)
    checks.append(("잘못된 secret 403", r.status_code == 403))

    r = client.post("/webhooks/imweb?secret=change-me", headers={"Authorization": "wrong"})
    checks.append(("잘못된 인증정보 403", r.status_code == 403))

    r = client.get("/erp/api/orders")
    orders = r.json()
    ok = (
        len(orders) == 1
        and orders[0]["order_no"] == "20260723000001"
        and orders[0]["store_name"] == "강남점"
        and orders[0]["pickup_date"] == "2026-07-26 14:00"
        and orders[0]["customer_name"] == "홍길동"
        and orders[0]["amount"] == 144000
        and "Radiant Glow Serum I" in orders[0]["items_summary"]
        and orders[0]["event_type"] == "ORDER_CREATE"
        and orders[0]["status"] == "결제대기"
        and orders[0]["section_code"] == "os20260723smoke"
        and orders[0]["member_uid"] == "hong@test.kr"
    )
    checks.append(("실스펙 파싱(지점/날짜/고객/금액/품목/상태/섹션코드/회원UID)", ok))

    r = client.get("/erp/api/inventory")
    gangnam_serum = next(
        i for i in r.json()
        if i["store_name"] == "강남점" and i["product_name"] == "Radiant Glow Serum I"
    )
    checks.append(("재고 차감 20→18 (섹션아이템 qty=2)", gangnam_serum["qty"] == 18))

    r = client.get("/public/stock", params={"product": "Radiant Glow Serum I"})
    rows = {x["store"]: x["qty"] for x in r.json()}
    checks.append(("공개 재고 API (강남 18/성수 20/천안 20)", rows.get("강남점") == 18 and rows.get("성수점") == 20 and rows.get("천안점") == 20))

    # 시드에 없는 상품 → 재고 자동 생성 후 차감
    unknown = json.loads(json.dumps(REAL_SPEC_WEBHOOK))
    unknown["data"]["orderNo"] = 20260723000002
    item = unknown["data"]["section"]["sectionItems"][0]
    item["productInfo"]["prodName"] = "Enchanté Signature Perfume"
    item["productInfo"]["optionInfo"] = {"지점선택": "성수점", "픽업 희망일": "2026-07-27"}
    item["qty"] = 3
    client.post("/webhooks/imweb?secret=change-me", content=json.dumps(unknown), headers=AUTH)
    r = client.get("/erp/api/inventory")
    new_inv = next(
        (i for i in r.json()
         if i["store_name"] == "성수점" and i["product_name"] == "Enchanté Signature Perfume"),
        None,
    )
    checks.append(("미등록 상품 재고 자동 생성 20→17", new_inv is not None and new_inv["qty"] == 17))

    r = client.get("/erp/api/orders")
    checks.append(("주문 2건 upsert", len(r.json()) == 2))

    order_id = [o for o in r.json() if o["order_no"] == "20260723000001"][0]["id"]
    r = client.post(f"/erp/api/orders/{order_id}/status", json={"status": "픽업대기"})
    checks.append(("상태 변경 → 픽업대기", r.status_code == 200))

    # 푸시 대상 상태(픽업완료) — 테스트 환경(IMWEB_PUSH_ENABLED=0)에선 synced=false여야 함
    r = client.post(f"/erp/api/orders/{order_id}/status", json={"status": "픽업완료"})
    checks.append(("픽업완료 변경 + 푸시 비활성 시 synced=false", r.status_code == 200 and r.json().get("imweb_synced") is False))

    # 취소 이벤트 수신 시 취소 전환
    cancel = json.loads(json.dumps(REAL_SPEC_WEBHOOK))
    cancel["eventType"] = "ORDER_CANCEL_COMPLETE"
    client.post("/webhooks/imweb?secret=change-me", content=json.dumps(cancel), headers=AUTH)
    r = client.get("/erp/api/orders")
    first = [o for o in r.json() if o["order_no"] == "20260723000001"][0]
    checks.append(("취소 이벤트 → 취소", first["status"] == "취소"))

    # 취소 후 진행 이벤트(입금완료 폴링)가 와도 취소 유지 (종결 랭크 가드)
    revert = json.loads(json.dumps(REAL_SPEC_WEBHOOK))
    revert["eventType"] = "API_POLL"
    revert["data"]["section"]["orderSectionStatus"] = "PRODUCT_PREPARATION"
    revert["data"]["payments"] = [{"paymentStatus": "PAYMENT_COMPLETE"}]
    client.post("/webhooks/imweb?secret=change-me", content=json.dumps(revert), headers=AUTH)
    r = client.get("/erp/api/orders")
    first = [o for o in r.json() if o["order_no"] == "20260723000001"][0]
    checks.append(("취소 가드 — 폴링이 취소를 되돌리지 않음", first["status"] == "취소"))

    # 미허용 상태 문자열은 422로 거부 (Literal 화이트리스트)
    r = client.post(f"/erp/api/orders/{order_id}/status", json={"status": "<script>"})
    checks.append(("미허용 상태 422 거부", r.status_code == 422))

    # 결제·배송 단계 매핑 (아임웹 탭 1:1) — 주문3으로 단계별 검증
    def send(event_type, section_status, order_no=20260723000003, extra=None):
        p = json.loads(json.dumps(REAL_SPEC_WEBHOOK))
        p["data"]["orderNo"] = order_no
        p["eventType"] = event_type
        p["data"]["section"]["orderSectionStatus"] = section_status
        if extra:
            p["data"].update(extra)
        client.post("/webhooks/imweb?secret=change-me", content=json.dumps(p), headers=AUTH)
        r = client.get("/erp/api/orders")
        return [o for o in r.json() if o["order_no"] == str(order_no)][0]["status"]

    checks.append(("주문 생성(미입금) → 결제대기", send("ORDER_CREATE", "PRODUCT_PREPARATION") == "결제대기"))
    checks.append(("폴링 paymentStatus=COMPLETE → 픽업대기",
                   send("API_POLL", "PRODUCT_PREPARATION",
                        extra={"payments": [{"paymentStatus": "PAYMENT_COMPLETE"}]}) == "픽업대기"))
    checks.append(("입금완료 이벤트 → 픽업대기", send("ORDER_DEPOSIT_COMPLETE", "PRODUCT_PREPARATION") == "픽업대기"))
    checks.append(("구 택배 SHIPPING_READY → 픽업대기 흡수", send("API_POLL", "SHIPPING_READY") == "픽업대기"))
    checks.append(("구 택배 SHIPPING → 픽업대기 흡수", send("API_POLL", "SHIPPING") == "픽업대기"))
    checks.append(("SHIPPING_COMPLETE(배송완료) → 픽업완료", send("API_POLL", "SHIPPING_COMPLETE") == "픽업완료"))
    # 진행 역행 방지: 픽업완료 후 PREPARATION 폴링이 와도 유지
    checks.append(("랭크 가드 — 픽업완료 유지", send("API_POLL", "PRODUCT_PREPARATION",
                   extra={"payments": [{"paymentStatus": "PAYMENT_COMPLETE"}]}) == "픽업완료"))

    # 입금 확인 전용 엔드포인트 — 푸시 비활성 환경에선 명시적 400 (조용한 실패 금지)
    r = client.get("/erp/api/orders")
    any_id = r.json()[0]["id"]
    r = client.post(f"/erp/api/orders/{any_id}/confirm-payment")
    checks.append(("입금확인 — 푸시 비활성 시 명시적 400", r.status_code == 400))

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), "-", name)
print()
print("결과:", f"{len(checks) - len(failed)}/{len(checks)} 통과")
raise SystemExit(1 if failed else 0)
