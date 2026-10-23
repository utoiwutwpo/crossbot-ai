"""客服红线层 + 差评闭环 + 验证闭环埋点"""
from fastapi.testclient import TestClient


def _auth(client: TestClient, email: str, plan: str = "free") -> dict:
    r = client.post("/api/v1/users/register", json={
        "email": email, "password": "Passw0rd!123"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if plan != "free":
        client.post("/api/v1/billing/subscription", headers=h,
                    json={"plan": plan})
    return h


# ---------- 客服红线层 ----------
def test_redline_negative_review_threat(client):
    h = _auth(client, "rl1@test.com", plan="pro")
    r = client.post("/api/v1/customer-service/messages", headers=h, json={
        "customer_message": "Refund me right now or I will leave a 1-star review and a chargeback!"})
    assert r.status_code == 200
    d = r.json()
    assert d["needs_escalation"] is True
    assert "refund_extortion" in d["policy_flags"]
    assert "negative_review_threat" in d["policy_flags"]
    assert d["guardrail"]                       # 红线说明存在
    # 红线话术不得包含任何承诺退款字样
    assert "24 hours" in d["reply"] and "refund me" not in d["reply"].lower()


def test_redline_harm_claim_escalates(client):
    h = _auth(client, "rl2@test.com", plan="pro")
    d = client.post("/api/v1/customer-service/messages", headers=h, json={
        "customer_message": "The charger caught fire and my son was hurt, I'm in hospital."}).json()
    assert "harm_claim" in d["policy_flags"]
    assert d["needs_escalation"] is True


def test_normal_message_no_redline(client):
    h = _auth(client, "rl3@test.com", plan="pro")
    d = client.post("/api/v1/customer-service/messages", headers=h, json={
        "customer_message": "Where is my order #123-4567890-1234567?"}).json()
    assert d["policy_flags"] == []
    assert d["guardrail"] is None


# ---------- 差评闭环 ----------
def test_review_insights_themes_and_bullets(client):
    h = _auth(client, "rv1@test.com")
    r = client.post("/api/v1/products/review-insights", headers=h, json={
        "reviews": ["Battery dies quickly and it's too small", "No instructions included"],
        "rating": 2, "material": "ABS"})
    assert r.status_code == 200
    d = r.json()
    themes = {t["theme"] for t in d["themes"]}
    assert {"battery", "size_fit", "instructions"} <= themes
    assert len(d["improved_bullets"]) >= 3
    assert d["sentiment"] == "very_negative"
    # 材质占位符已被替换
    assert "ABS" in d["themes"][0]["bullet_fix"]["content"] or all(
        "{material}" not in t["bullet_fix"]["content"] for t in d["themes"])


def test_review_insights_consumes_quota(client):
    """免费版 5 次/天：差评分析复用同池额度。"""
    h = _auth(client, "rv2@test.com")
    payload = {"reviews": ["broke after two days"], "rating": 1}
    for _ in range(5):
        assert client.post("/api/v1/products/review-insights", headers=h,
                           json=payload).status_code == 200
    r = client.post("/api/v1/products/review-insights", headers=h, json=payload)
    assert r.status_code == 402     # 额度闸门照常生效


# ---------- 验证闭环埋点 ----------
def test_track_event_ok(client):
    r = client.post("/api/v1/analytics/track", json={"event_type": "landing_view",
                                                     "utm_source": "reddit"})
    assert r.status_code == 200


def test_track_invalid_event_422(client):
    assert client.post("/api/v1/analytics/track",
                       json={"event_type": "hax"}).status_code == 422


def test_summary_requires_admin_token(client):
    assert client.get("/api/v1/analytics/summary").status_code == 403
    assert client.get("/api/v1/analytics/summary",
                      headers={"X-Admin-Token": "wrong"}).status_code == 403


def test_summary_funnel_counts(client):
    # admin_token 默认为空 → 未配置即拒绝；这里通过 monkeypatch 配置临时值
    from app.config import settings
    old = settings.admin_token
    settings.admin_token = "test-admin-token"
    try:
        client.post("/api/v1/analytics/track", json={
            "event_type": "landing_view", "utm_source": "fb_pl"})
        client.post("/api/v1/products/gpsr/check-guest", json={
            "product_name": "Toy Blocks", "keywords": ["toy"], "platform": "allegro"})
        client.post("/api/v1/users/register?utm_source=fb_pl", json={
            "email": "funnel@test.com", "password": "Passw0rd!123"})
        h = {"Authorization": "Bearer " + client.post(
            "/api/v1/users/login", json={
                "email": "funnel@test.com", "password": "Passw0rd!123"}
        ).json()["access_token"]}
        client.post("/api/v1/products/descriptions/generate", headers=h, json={
            "product_name": "Toy Blocks", "keywords": ["toy"], "platform": "amazon"})

        r = client.get("/api/v1/analytics/summary?days=30",
                       headers={"X-Admin-Token": "test-admin-token"})
        assert r.status_code == 200
        d = r.json()
        f = d["funnel"]
        assert f["landing_view"] >= 1 and f["guest_check"] >= 1
        assert f["signup"] >= 1 and f["generate"] >= 1
        assert d["by_source"].get("fb_pl", {}).get("landing_view", 0) >= 1
        assert "check_to_signup" in d["conversion"]
    finally:
        settings.admin_token = old
