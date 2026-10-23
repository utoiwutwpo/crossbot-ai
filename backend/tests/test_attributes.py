"""属性树校验 + Kaufland/bol.com 注册表"""
from fastapi.testclient import TestClient


def _auth(client: TestClient) -> dict:
    r = client.post("/api/v1/users/register", json={
        "email": "attr@test.com", "password": "Passw0rd!123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------- 注册表 ----------
def test_registry_contains_kaufland_and_bol(client):
    r = client.get("/api/v1/products/platforms")
    assert r.status_code == 200
    reg = r.json()
    assert "kaufland" in reg and "bol" in reg
    assert reg["bol"]["language"] == "nl"
    assert reg["kaufland"]["language"] == "de"


def test_bol_language_nl_generates(client):
    h = _auth(client)
    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Bike Phone Mount", "keywords": ["bike", "phone"],
        "platform": "bol", "language": None})
    assert r.status_code == 200
    assert r.json()["language"] == "nl"   # bol 默认荷兰语


# ---------- 属性树引擎 ----------
def test_allegro_tree_has_hard_requirements(client):
    r = client.get("/api/v1/products/attributes/allegro")
    assert r.status_code == 200
    hard = {a["key"] for a in r.json()["attributes"] if a["required"] == "hard"}
    assert {"brand", "ean", "condition"} <= hard


def test_bol_missing_ean_blocks_listing(client):
    r = client.post("/api/v1/products/attributes/validate", json={
        "platform": "bol", "attributes": {"brand": "X"}})
    d = r.json()
    assert d["ready_to_list"] is False
    assert any("EAN" in b for b in d["blockers"])


def test_valid_ean_passes_and_counts_completeness(client):
    r = client.post("/api/v1/products/attributes/validate", json={
        "platform": "bol",
        "attributes": {"ean": "8712345678906", "brand": "X",
                       "model": "BL-77", "packaging_language": "nl"}})
    d = r.json()
    assert d["ready_to_list"] is True
    assert d["completeness"] == 100.0


def test_fake_ean_checksum_rejected(client):
    r = client.post("/api/v1/products/attributes/validate", json={
        "platform": "allegro", "attributes": {"ean": "1234567890123", "brand": "Y", "condition": "new"}})
    d = r.json()
    assert d["ready_to_list"] is False
    assert any(i["key"] == "ean" for i in d["invalid"])


def test_unknown_platform_attribute_tree_404(client):
    assert client.get("/api/v1/products/attributes/nonexistent").status_code == 404


def test_category_auto_detection():
    from app.experts.attributes import detect_category
    assert detect_category(["bluetooth", "baby"], "Baby Monitor") == "electronics"
    assert detect_category(["积木", "玩具"], "积木套装") == "toys"
