"""
GPSR 合规引擎验收测试（免费体检钩子 + 付费合规块 + 描述生成集成）
"""
from tests.conftest import register_and_login


# ---------- 纯规则层（零 LLM） ----------
def test_toy_detection_triggers_ce():
    from app.experts.gpsr import check
    r = check("Wooden Train Toy Set", ["toy", "kids"], "amazon")
    assert r["ce_required"] is True
    assert r["risk_level"] == "high"
    assert "2009/48/EC" in " ".join(r["ce_directives"])
    assert "玩具" in r["matched_categories"]


def test_bluetooth_product_triggers_red_and_lvd():
    from app.experts.gpsr import check
    r = check("Smart Sleep Mask with Bluetooth", ["bluetooth", "eye mask"], "otto")
    dirs = " ".join(r["ce_directives"])
    assert "2014/53/EU" in dirs          # 无线电 RED
    assert "2014/35/EU" in dirs          # 低压 LVD（mask 关键词命中 electrical）
    assert r["risk_level"] == "high"


def test_low_risk_product_no_ce():
    from app.experts.gpsr import check
    r = check("Handwoven Wall Tapestry", ["tapestry", "decor"], "amazon")
    assert r["ce_required"] is False
    assert r["risk_level"] == "low"
    assert r["ce_directives"] == []


def test_required_languages_match_platform_markets():
    from app.experts.gpsr import required_languages
    assert required_languages("allegro")[0] == "pl"   # 主市场波兰语优先
    assert set(required_languages("allegro")) == {"pl", "cs", "hu"}  # 覆盖 PL/CZ/HU
    assert required_languages("otto") == ["de"]
    assert required_languages("cdiscount") == ["fr"]
    assert "en" in required_languages("tiktok")  # TikTok Shop 英美
    assert "de" in required_languages("amazon")   # Amazon EU 覆盖德国


def test_gpsr_block_localized_warnings():
    from app.experts.gpsr import check
    r = check("Baby Pacifier", ["baby", "infant"], "cdiscount")
    block = r["gpsr_block"]
    assert "[FR]" in block                       # 法语警示语
    assert "Ne jamais laisser l'enfant" in block
    assert "[欧代公司名称]" in block              # 欧代占位符


# ---------- API 层 ----------
def test_gpsr_check_free_plan_masks_block(client):
    headers = register_and_login(client, "gpsr_free@test.com")   # 默认 free
    r = client.post("/api/v1/products/gpsr/check", headers=headers, json={
        "product_name": "RC Toy Car", "keywords": ["toy", "remote control"],
        "platform": "amazon",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["ce_required"] is True
    assert len(d["checklist"]) >= 7
    assert d["gpsr_block"] is None               # 免费版脱敏
    assert d["upsell_note"] is not None          # 付费钩子


def test_gpsr_check_paid_plan_unlocks_block(client):
    headers = register_and_login(client, "gpsr_pro@test.com")
    client.post("/api/v1/billing/subscription", headers=headers,
                json={"plan": "starter"})
    r = client.post("/api/v1/products/gpsr/check", headers=headers, json={
        "product_name": "RC Toy Car", "keywords": ["toy"], "platform": "allegro",
    })
    d = r.json()
    assert d["gpsr_block"] is not None
    assert "[PL]" in d["gpsr_block"]             # Allegro → 波兰语警示
    assert d["upsell_note"] is None


def test_gpsr_check_consumes_no_quota(client):
    headers = register_and_login(client, "gpsr_quota@test.com")
    before = client.get("/api/v1/billing/subscription", headers=headers).json()
    for _ in range(5):                           # 连续体检 5 次
        r = client.post("/api/v1/products/gpsr/check", headers=headers, json={
            "product_name": "LED Lamp", "keywords": ["led"], "platform": "otto"})
        assert r.status_code == 200
    after = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert after["usage_today"] == before["usage_today"]   # 体检免费不计数


def test_gpsr_check_requires_auth(client):
    r = client.post("/api/v1/products/gpsr/check", json={
        "product_name": "Toy", "keywords": ["toy"], "platform": "amazon"})
    assert r.status_code in (401, 403)


# ---------- 与产品描述生成集成 ----------
def test_description_includes_gpsr_block_for_ce_category(client):
    headers = register_and_login(client, "gpsr_desc@test.com")
    r = client.post("/api/v1/products/descriptions/generate", headers=headers,
                    json={"product_name": "Kids Building Blocks Toy",
                          "keywords": ["toy", "puzzle"], "platform": "otto"})
    assert r.status_code == 200
    d = r.json()
    assert d["gpsr_risk_level"] == "high"
    assert d["gpsr_block"] and "[DE]" in d["gpsr_block"]


def test_description_without_gpsr_for_non_ce(client):
    headers = register_and_login(client, "gpsr_plain@test.com")
    r = client.post("/api/v1/products/descriptions/generate", headers=headers,
                    json={"product_name": "Handwoven Wall Tapestry",
                          "keywords": ["decor"], "platform": "amazon"})
    assert r.status_code == 200
    d = r.json()
    assert d["gpsr_risk_level"] is None
    assert d["gpsr_block"] is None


# ---------- 游客体检端点（免注册 + IP 限频） ----------
def test_guest_check_no_auth_needed(client):
    r = client.post("/api/v1/products/gpsr/check-guest", json={
        "product_name": "Bluetooth Baby Monitor", "keywords": ["baby", "bluetooth"], "platform": "otto"})
    assert r.status_code == 200
    d = r.json()
    assert d["risk_level"] == "high"
    assert d["gpsr_block"] is None           # 游客版固定脱敏
    assert d["upsell_note"]                  # 保留付费/注册钩子


def test_guest_check_rate_limited(client):
    from app.routers.products import _GUEST_HITS
    _GUEST_HITS.clear()   # 限频状态是模块级内存，先重置保证用例确定性
    payload = {"product_name": "Kids Toy Blocks", "keywords": ["toy"], "platform": "amazon"}
    for _ in range(3):
        assert client.post("/api/v1/products/gpsr/check-guest", json=payload).status_code == 200
    r = client.post("/api/v1/products/gpsr/check-guest", json=payload)
    assert r.status_code == 429
    assert "注册" in r.json()["detail"]
