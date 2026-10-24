"""
获客落地页路由 + ASIN 支持测试
"""
from tests.conftest import register_and_login


def test_landing_routes_served(client):
    for path in ("/gpsr-check", "/gpsr-check/pl", "/gpsr-check/ro"):
        r = client.get(path)
        assert r.status_code == 200
        assert "GPSR" in r.text


def test_site_structure_routes(client):
    """/ 营销主页、/app 工作台、/pricing 定价页、/skills 开源页四段式站点结构"""
    r = client.get("/")
    assert r.status_code == 200
    assert "免费开始" in r.text and "/gpsr-check" in r.text   # 营销主页，不强制登录
    r = client.get("/app")
    assert r.status_code == 200
    assert "独立工作台" in r.text                              # 工作台
    r = client.get("/pricing")
    assert r.status_code == 200
    assert "€29" in r.text and "€79" in r.text                # 定价页含档位
    r = client.get("/skills")
    assert r.status_code == 200
    assert "MIT" in r.text and "gpsr-compliance-checker" in r.text  # 开源 Skills 页


def test_gpsr_check_accepts_asin(client):
    headers = register_and_login(client, "asin1@test.com")
    r = client.post("/api/v1/products/gpsr/check", headers=headers, json={
        "product_name": "Wooden Toy Train", "keywords": ["toy"],
        "platform": "amazon", "asin": "B0C1234XYZ"})
    assert r.status_code == 200
    d = r.json()
    assert d["asin"] == "B0C1234XYZ"
    assert d["data_source"] == "title_keywords"   # 如实标注判定来源


def test_gpsr_check_rejects_bad_asin(client):
    headers = register_and_login(client, "asin2@test.com")
    r = client.post("/api/v1/products/gpsr/check", headers=headers, json={
        "product_name": "Toy", "keywords": ["toy"],
        "platform": "amazon", "asin": "SHORT"})
    assert r.status_code == 422
