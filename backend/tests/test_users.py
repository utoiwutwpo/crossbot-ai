"""用户认证与套餐 API 验收"""
from tests.conftest import register_and_login


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["llm_mode"] == "mock"


def test_register_and_me(client):
    headers = register_and_login(client, "alice@test.com")
    r = client.get("/api/v1/users/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "alice@test.com"
    assert r.json()["plan"] == "free"


def test_duplicate_register_rejected(client):
    r1 = client.post("/api/v1/users/register", json={
        "email": "dup@test.com", "password": "Passw0rd!123"})
    assert r1.status_code == 200
    r2 = client.post("/api/v1/users/register", json={
        "email": "dup@test.com", "password": "Passw0rd!123"})
    assert r2.status_code == 409


def test_login_wrong_password(client):
    client.post("/api/v1/users/register", json={
        "email": "bob@test.com", "password": "Passw0rd!123"})
    r = client.post("/api/v1/users/login", json={
        "email": "bob@test.com", "password": "wrong-pass"})
    assert r.status_code == 401


def test_unauthenticated_rejected(client):
    r = client.get("/api/v1/users/me")
    assert r.status_code == 401


def test_subscription_upgrade_and_cancel(client):
    headers = register_and_login(client, "carol@test.com")

    r = client.post("/api/v1/billing/subscription",
                    json={"plan": "pro"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"

    s = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert s["plan"] == "pro"
    assert s["daily_limit"] == 200

    r = client.delete("/api/v1/billing/subscription", headers=headers)
    assert r.status_code == 200
    s = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert s["plan"] == "free"


# ---------- Google 登录 + 独立登录/注册页 ----------
def test_google_config_disabled_by_default(client):
    r = client.get("/api/v1/users/google-config")
    assert r.status_code == 200
    d = r.json()
    assert d["enabled"] is False
    assert d["client_id"] == ""


def test_google_login_unconfigured_returns_501(client):
    r = client.post("/api/v1/users/google", json={"credential": "x" * 40})
    assert r.status_code == 501
    assert "GOOGLE_CLIENT_ID" in r.json()["detail"]


def test_signin_signup_pages_exist(client):
    assert client.get("/signin").status_code == 200
    assert client.get("/signup").status_code == 200
