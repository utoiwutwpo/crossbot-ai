"""Stripe + PayPal 收款集成测试（无真实 Key：测纯函数 + 本地模式 + webhook 联调路径）"""
import json

from app import stripe_service, paypal_service
from app.config import settings


def test_map_price_to_plan(monkeypatch):
    monkeypatch.setattr(settings, "stripe_price_starter", "price_start_123")
    monkeypatch.setattr(settings, "stripe_price_pro", "price_pro_456")
    assert stripe_service.map_price_to_plan("price_start_123") == "starter"
    assert stripe_service.map_price_to_plan("price_pro_456") == "pro"
    assert stripe_service.map_price_to_plan("price_unknown") is None
    assert stripe_service.map_price_to_plan("") is None


def test_checkout_requires_config(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    try:
        stripe_service.create_checkout_session(
            type("U", (), {"email": "x@test.com"})(), "starter", "http://x")
        assert False, "should raise"
    except ValueError as e:
        assert "stripe_secret_key" in str(e)


def test_checkout_rejects_free_plan():
    """free 不可购买（free 是取消，不是结账）"""
    try:
        stripe_service.create_checkout_session(
            type("U", (), {"email": "x@test.com"})(), "free", "http://x")
        assert False, "should raise"
    except ValueError as e:
        assert "purchasable" in str(e)


def test_subscription_local_mode_still_works(client):
    """未配 Stripe Key 时 POST /subscription 走本地模拟（演示路径不被破坏）"""
    from tests.conftest import register_and_login
    headers = register_and_login(client, "pay1@test.com")
    r = client.post("/api/v1/billing/subscription", headers=headers,
                    json={"plan": "starter"})
    assert r.status_code == 200
    d = r.json()
    assert d["plan"] == "starter"


def test_webhook_debug_mode_opens_plan(client):
    """未配 Key 的联调模式：webhook 可直接解析事件并开通套餐"""
    from tests.conftest import register_and_login
    headers = register_and_login(client, "pay2@test.com")
    # 拿到用户 id
    me = client.get("/api/v1/users/me", headers=headers).json()

    event = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "client_reference_id": me["id"],
            "metadata": {"user_id": me["id"], "plan": "pro"},
            "customer": "cus_test_1",
            "subscription": "sub_test_1",
        }},
    }
    r = client.post("/api/v1/billing/webhook", json=event)
    assert r.status_code == 200
    assert r.json()["user_found"] is True
    sub = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert sub["plan"] == "pro"
    assert sub["stripe_status"] == "active"


def test_webhook_subscription_deleted_downgrades(client):
    from tests.conftest import register_and_login
    headers = register_and_login(client, "pay3@test.com")
    me = client.get("/api/v1/users/me", headers=headers).json()
    client.post("/api/v1/billing/webhook", json={
        "type": "checkout.session.completed",
        "data": {"object": {"client_reference_id": me["id"],
                            "metadata": {"user_id": me["id"], "plan": "business"}}}})
    # 退订事件 → 降回 free
    r = client.post("/api/v1/billing/webhook", json={
        "type": "customer.subscription.deleted",
        "data": {"object": {"client_reference_id": me["id"]}}})
    assert r.status_code == 200
    sub = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert sub["plan"] == "free"
    assert sub["stripe_status"] == "canceled"


# ---------- PayPal ----------

def test_paypal_map_plan_id(monkeypatch):
    monkeypatch.setattr(settings, "paypal_plan_pro", "P-PRO-1")
    assert paypal_service.map_plan_id_to_plan("P-PRO-1") == "pro"
    assert paypal_service.map_plan_id_to_plan("P-UNKNOWN") is None
    assert paypal_service.map_plan_id_to_plan("") is None


def test_paypal_requires_config(monkeypatch):
    monkeypatch.setattr(settings, "paypal_client_id", "")
    assert paypal_service.configured() is False


def test_paypal_subscription_endpoint_501_without_config(client, monkeypatch):
    """未配置 PayPal：端点返回 501（引导走 Stripe/本地模式）"""
    from tests.conftest import register_and_login
    monkeypatch.setattr(settings, "paypal_client_id", "")
    headers = register_and_login(client, "pay4@test.com")
    r = client.post("/api/v1/billing/paypal/subscription", headers=headers,
                    json={"plan": "starter"})
    assert r.status_code == 501


def test_paypal_webhook_debug_mode_activates(client, monkeypatch):
    """未配置 webhook_id：联调模式直接解析事件并开通套餐"""
    from tests.conftest import register_and_login
    monkeypatch.setattr(settings, "paypal_client_id", "")
    monkeypatch.setattr(settings, "paypal_plan_pro", "P-PRO-9")
    headers = register_and_login(client, "pay5@test.com")
    me = client.get("/api/v1/users/me", headers=headers).json()
    r = client.post("/api/v1/billing/paypal/webhook", json={
        "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
        "resource": {"custom_id": me["id"], "id": "I-TEST",
                     "plan_id": "P-PRO-9",
                     "subscriber": {"payer_id": "PAYPALU1"}}})
    assert r.status_code == 200
    assert r.json()["action"] == "activated"
    sub = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert sub["plan"] == "pro"
    assert sub["stripe_status"] == "active"


def test_paypal_webhook_cancel_downgrades(client, monkeypatch):
    from tests.conftest import register_and_login
    monkeypatch.setattr(settings, "paypal_client_id", "")
    headers = register_and_login(client, "pay6@test.com")
    me = client.get("/api/v1/users/me", headers=headers).json()
    client.post("/api/v1/billing/paypal/webhook", json={
        "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
        "resource": {"custom_id": me["id"], "plan_id": "P-X",
                     "subscriber": {}}})
    r = client.post("/api/v1/billing/paypal/webhook", json={
        "event_type": "BILLING.SUBSCRIPTION.CANCELLED",
        "resource": {"custom_id": me["id"]}})
    assert r.status_code == 200
    sub = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert sub["plan"] == "free"
