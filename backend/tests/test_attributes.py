"""属性树校验 + Kaufland/Zalando/bol.com 注册表"""
from fastapi.testclient import TestClient


def _auth(client: TestClient) -> dict:
    r = client.post("/api/v1/users/register", json={
        "email": "attr@test.com", "password": "Passw0rd!123"})
    if r.status_code == 409:   # 同一测试会话内已注册过 → 直接登录
        r = client.post("/api/v1/users/login", json={
            "email": "attr@test.com", "password": "Passw0rd!123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------- 注册表 ----------
def test_registry_contains_kaufland_zalando_bol(client):
    r = client.get("/api/v1/products/platforms")
    assert r.status_code == 200
    reg = r.json()
    assert "kaufland" in reg and "zalando" in reg and "bol" in reg
    assert reg["zalando"]["language"] == "en"
    assert reg["kaufland"]["language"] == "de"
    assert reg["bol"]["language"] == "nl"


def test_bol_language_nl_generates(client):
    h = _auth(client)
    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Bike Phone Mount", "keywords": ["bike", "phone"],
        "platform": "bol", "language": None})
    assert r.status_code == 200
    assert r.json()["language"] == "nl"   # bol 默认荷兰语


def test_zalando_generates_with_english_default(client):
    h = _auth(client)
    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Running Jacket", "keywords": ["jacket", "running"],
        "platform": "zalando", "language": None})
    assert r.status_code == 200
    assert r.json()["language"] == "en"   # zalando 主目录默认英语


def test_amazon_us_generates_english(client):
    h = _auth(client)
    r = client.post("/api/v1/products/descriptions/generate", headers=h, json={
        "product_name": "Bike Phone Mount", "keywords": ["bike", "phone"],
        "platform": "amazon_us", "language": None})
    assert r.status_code == 200
    assert r.json()["language"] == "en"   # 美国站默认英语


def test_amazon_us_registry_rules(client):
    r = client.get("/api/v1/products/platforms")
    assert r.status_code == 200
    reg = r.json()
    assert "amazon_us" in reg
    assert reg["amazon_us"]["countries"] == ["US"]
    assert reg["amazon_us"]["title_max"] == 200


# ---------- 属性树引擎 ----------
def test_allegro_tree_has_hard_requirements(client):
    r = client.get("/api/v1/products/attributes/allegro")
    assert r.status_code == 200
    hard = {a["key"] for a in r.json()["attributes"] if a["required"] == "hard"}
    assert {"brand", "ean", "condition"} <= hard


def test_zalando_missing_ean_blocks_listing(client):
    r = client.post("/api/v1/products/attributes/validate", json={
        "platform": "zalando", "attributes": {"brand": "X"}})
    d = r.json()
    assert d["ready_to_list"] is False
    assert any("EAN" in b for b in d["blockers"])


def test_bol_missing_ean_blocks_listing(client):
    r = client.post("/api/v1/products/attributes/validate", json={
        "platform": "bol", "attributes": {"brand": "X"}})
    d = r.json()
    assert d["ready_to_list"] is False
    assert any("EAN" in b for b in d["blockers"])


def test_bol_valid_full_passes(client):
    r = client.post("/api/v1/products/attributes/validate", json={
        "platform": "bol",
        "attributes": {"ean": "8712345678906", "brand": "X",
                       "model": "BL-77", "packaging_language": "nl"}})
    d = r.json()
    assert d["ready_to_list"] is True
    assert d["completeness"] == 100.0


def test_zalando_missing_material_composition_blocks(client):
    r = client.post("/api/v1/products/attributes/validate", json={
        "platform": "zalando",
        "attributes": {"ean": "8712345678906", "brand": "X", "size_grid": "EU 36-46"}})
    d = r.json()
    assert d["ready_to_list"] is False
    assert any("材质" in b for b in d["blockers"])


def test_valid_ean_passes_and_counts_completeness(client):
    r = client.post("/api/v1/products/attributes/validate", json={
        "platform": "zalando",
        "attributes": {"ean": "8712345678906", "brand": "X",
                       "material_composition": "80% Cotton, 20% Polyester",
                       "size_grid": "EU 36-46", "care_instructions": "Machine wash 30°C",
                       "model": "ZL-2210"}})
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
