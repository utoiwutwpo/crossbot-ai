"""计费闸门验收：免费额度 / 功能门控"""
from tests.conftest import register_and_login

DESC_BODY = {
    "product_name": "Test Product",
    "keywords": ["test"],
    "platform": "amazon",
}


def test_free_plan_daily_limit_enforced(client):
    """免费版每日 5 次：第 6 次必须 402"""
    headers = register_and_login(client, "quota@test.com")
    for i in range(5):
        r = client.post("/api/v1/products/descriptions/generate",
                        json=DESC_BODY, headers=headers)
        assert r.status_code == 200, f"第 {i+1} 次应成功"
    r = client.post("/api/v1/products/descriptions/generate",
                    json=DESC_BODY, headers=headers)
    assert r.status_code == 402
    assert "额度" in r.json()["detail"]


def test_free_plan_feature_gating(client):
    """免费版不含 AI 客服/广告文案，必须 402 门控"""
    headers = register_and_login(client, "gate@test.com")
    r = client.post("/api/v1/customer-service/messages", json={
        "customer_message": "hello"}, headers=headers)
    assert r.status_code == 402
    assert "升级" in r.json()["detail"]

    r = client.post("/api/v1/ads/generate", json={
        "product_name": "X", "platform": "google",
        "target_audience": "a", "unique_selling_point": "b"},
        headers=headers)
    assert r.status_code == 402


def test_pro_plan_unlocks_all_features(client):
    """Pro 升级后客服/广告可用"""
    headers = register_and_login(client, "pro@test.com")
    client.post("/api/v1/billing/subscription",
                json={"plan": "pro"}, headers=headers)
    r = client.post("/api/v1/customer-service/messages", json={
        "customer_message": "Do you ship to Germany?"}, headers=headers)
    assert r.status_code == 200
    r = client.post("/api/v1/ads/generate", json={
        "product_name": "X", "platform": "google",
        "target_audience": "a", "unique_selling_point": "b"},
        headers=headers)
    assert r.status_code == 200
