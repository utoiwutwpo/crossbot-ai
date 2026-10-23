"""三大 AI 专家（Mock 模式）验收"""
from tests.conftest import register_and_login

DESC_BODY = {
    "product_name": "Wireless Noise Cancelling Headphones",
    "keywords": ["wireless", "bluetooth", "noise cancelling"],
    "platform": "amazon",
    "language": "en",
}


# ---------- 产品描述 ----------
def test_generate_description_valid_structure(client):
    headers = register_and_login(client, "desc1@test.com")
    r = client.post("/api/v1/products/descriptions/generate",
                    json=DESC_BODY, headers=headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["title"], "标题不能为空"
    assert len(d["bullet_points"]) == 5, "Amazon 必须恰好 5 点描述"
    assert d["description"] and d["search_terms"]
    assert 0 <= d["optimization_score"] <= 100
    assert d["platform_compliant"] is True
    assert d["id"], "生成结果应已落库"


def test_description_history_persisted(client):
    headers = register_and_login(client, "desc2@test.com")
    client.post("/api/v1/products/descriptions/generate",
                json=DESC_BODY, headers=headers)
    r = client.get("/api/v1/products/descriptions", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert body["items"][0]["product_name"] == DESC_BODY["product_name"]


def test_description_platform_compliance_ebay_title_limit(client):
    """eBay 标题上限 80 字符，生成结果必须合规"""
    headers = register_and_login(client, "desc3@test.com")
    body = {**DESC_BODY, "platform": "ebay"}
    d = client.post("/api/v1/products/descriptions/generate",
                    json=body, headers=headers).json()
    assert len(d["title"]) <= 80 or not d["platform_compliant"]
    # 违规时必须给出 violations 说明
    if not d["platform_compliant"]:
        assert d["violations"]


# ---------- AI 客服 ----------
# 客服/广告是 Pro 功能，免费版 402 门控（该行为由 test_billing.py 覆盖），
# 本节测试先升级 Pro 再验证专家逻辑。
def _upgrade_pro(client, headers):
    r = client.post("/api/v1/billing/subscription",
                    json={"plan": "pro"}, headers=headers)
    assert r.status_code == 200


def test_cs_tracking_intent_with_order(client):
    headers = register_and_login(client, "cs1@test.com")
    _upgrade_pro(client, headers)
    r = client.post("/api/v1/customer-service/messages", json={
        "customer_message": "Where is my order #123-4567890-1234567?",
    }, headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "tracking"
    assert "123-4567890-1234567" in d["reply"]
    assert d["needs_escalation"] is False


def test_cs_complaint_negative_escalates(client):
    headers = register_and_login(client, "cs2@test.com")
    _upgrade_pro(client, headers)
    r = client.post("/api/v1/customer-service/messages", json={
        "customer_message": "This product arrived broken and I am angry. Terrible quality, I want a refund now!",
    }, headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["sentiment"] in ("negative", "very_negative")
    assert d["needs_escalation"] is True
    assert d["escalation_reason"]


# ---------- 广告文案 ----------
def test_ad_copy_facebook_length_limits(client):
    headers = register_and_login(client, "ad1@test.com")
    _upgrade_pro(client, headers)
    r = client.post("/api/v1/ads/generate", json={
        "product_name": "Smart Water Bottle",
        "platform": "facebook",
        "target_audience": "fitness enthusiasts",
        "unique_selling_point": "Tracks hydration and glows to remind you to drink",
    }, headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert len(d["primary_text"]) <= 125
    assert len(d["headline"]) <= 40
    assert len(d["description"]) <= 30
    assert d["cta"]
    assert 1 <= len(d["hashtags"]) <= 5
