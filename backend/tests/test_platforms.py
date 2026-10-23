"""欧洲平台接入验收：注册表 / 语言自动匹配 / 多平台矩阵"""
import pytest

from tests.conftest import register_and_login

EU_PLATFORMS = [
    "amazon", "ebay", "cdiscount", "otto", "allegro",
    "emag", "walmart", "fruugo", "tiktok",
]

REQUIRED_KEYS = [
    "display", "countries", "language", "title_max", "bullets",
    "search_terms_max", "description_max", "notes",
]

EXPECTED_DEFAULT_LANGUAGE = {
    "amazon": "en", "ebay": "en", "fruugo": "en", "walmart": "en",
    "cdiscount": "fr", "otto": "de", "allegro": "pl",
    "emag": "ro", "tiktok": "en",
}


# ---------- 注册表 ----------
def test_registry_covers_all_eu_platforms():
    from app.experts.platform_registry import PLATFORMS
    for p in EU_PLATFORMS:
        assert p in PLATFORMS, f"缺少平台 {p}"
        cfg = PLATFORMS[p]
        for k in REQUIRED_KEYS:
            assert k in cfg, f"{p} 缺少字段 {k}"
        assert cfg["title_max"] > 0
        assert cfg["bullets"] == 5
        assert 0 < cfg["search_terms_max"] <= 1000


def test_registry_default_languages():
    """语言自动匹配：Allegro→pl Otto→de Cdiscount→fr eMAG→ro TikTok→en"""
    from app.experts.platform_registry import PLATFORMS
    for p, lang in EXPECTED_DEFAULT_LANGUAGE.items():
        assert PLATFORMS[p]["language"] == lang


def test_platforms_api(client):
    r = client.get("/api/v1/products/platforms")
    assert r.status_code == 200
    body = r.json()
    for p in EU_PLATFORMS:
        assert p in body


# ---------- 单平台生成：语言自动匹配 + 合规 ----------
@pytest.mark.parametrize("platform,lang", [
    ("allegro", "pl"), ("otto", "de"), ("cdiscount", "fr"),
    ("emag", "ro"), ("tiktok", "en"), ("walmart", "en"), ("fruugo", "en"),
])
def test_generate_auto_language_and_limits(client, platform, lang):
    headers = register_and_login(client, f"auto-{platform}@test.com")
    r = client.post("/api/v1/products/descriptions/generate", json={
        "product_name": "Smart Sleep Mask",
        "keywords": ["sleep", "bluetooth"],
        "platform": platform,
        # 故意不传 language → 必须自动用平台默认
    }, headers=headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["language"] == lang, f"{platform} 默认语言应为 {lang}"
    assert d["platform"] == platform

    from app.experts.platform_registry import PLATFORMS
    title_max = PLATFORMS[platform]["title_max"]
    if len(d["title"]) > title_max:
        assert not d["platform_compliant"] and d["violations"]
    else:
        assert d["platform_compliant"] is True
    assert len(d["bullet_points"]) == 5


def test_explicit_language_overrides_default(client):
    headers = register_and_login(client, "override@test.com")
    d = client.post("/api/v1/products/descriptions/generate", json={
        "product_name": "Yoga Mat", "keywords": ["yoga"],
        "platform": "otto", "language": "en"},  # 明确指定英语 → 覆盖德语默认
        headers=headers).json()
    assert d["language"] == "en"


# ---------- 多平台矩阵 ----------
def test_market_matrix_generates_all_platforms(client):
    headers = register_and_login(client, "matrix@test.com")
    client.post("/api/v1/billing/subscription",
                json={"plan": "pro"}, headers=headers)
    r = client.post("/api/v1/products/descriptions/market-matrix", json={
        "product_name": "Smart Sleep Mask",
        "keywords": ["sleep", "bluetooth"],
        "platforms": ["allegro", "otto", "cdiscount", "emag", "tiktok"],
    }, headers=headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["requested"] == 5
    assert d["succeeded"] == 5
    assert not d["errors"]
    langs = {x["platform"]: x["language"] for x in d["results"]}
    assert langs == {"allegro": "pl", "otto": "de", "cdiscount": "fr",
                     "emag": "ro", "tiktok": "en"}
    # 全部落库
    history = client.get("/api/v1/products/descriptions?page_size=50",
                         headers=headers).json()
    assert history["total"] >= 5


def test_market_matrix_dedupes_platforms(client):
    headers = register_and_login(client, "matrixdup@test.com")
    client.post("/api/v1/billing/subscription",
                json={"plan": "pro"}, headers=headers)
    d = client.post("/api/v1/products/descriptions/market-matrix", json={
        "product_name": "X", "keywords": ["k"],
        "platforms": ["ebay", "ebay", "fruugo", "ebay"]},
        headers=headers).json()
    assert d["requested"] == 2
    assert d["succeeded"] == 2


def test_matrix_respects_free_quota(client):
    """免费版日限 5 次：9 平台矩阵应生成 5 个 + 额度报错"""
    headers = register_and_login(client, "matrixfree@test.com")
    d = client.post("/api/v1/products/descriptions/market-matrix", json={
        "product_name": "X", "keywords": ["k"],
        "platforms": EU_PLATFORMS},  # 9 个平台
        headers=headers).json()
    assert d["succeeded"] == 5
    assert d["requested"] == 9
    assert len(d["errors"]) == 1
    assert "额度不足" in d["errors"][0]["error"]


def test_matrix_rejects_invalid_platform(client):
    headers = register_and_login(client, "matrixbad@test.com")
    r = client.post("/api/v1/products/descriptions/market-matrix", json={
        "product_name": "X", "keywords": ["k"],
        "platforms": ["taobao"]}, headers=headers)  # 未接入的平台
    assert r.status_code == 422  # Pydantic Literal 校验拦截
