"""
安全事件预警（GPSR Art.35 15 天上报闭环）
"""
from tests.conftest import register_and_login


def test_safety_word_hit_triggers_alert():
    """安全词命中 → incident + 15 天上报行动清单"""
    from app.experts.safety_gate import scan_reviews
    r = scan_reviews(["My power bank caught fire and started smoking, "
                      "almost burned my desk!"])
    assert r["incident_detected"] is True
    assert "fire_thermal" in r["categories_hit"]
    assert any("15" in s for s in r["action_steps"])
    assert "15" in r["deadline_note"]
    assert r["data_source"] == "safety_lexicon_scan"


def test_safety_clean_reviews_no_alert():
    """普通差评（质量/物流）不误报"""
    from app.experts.safety_gate import scan_reviews
    r = scan_reviews(["Took weeks to arrive and the box was crushed.",
                      "Battery dies quickly, not worth it."])
    assert r["incident_detected"] is False
    assert r["action_steps"] is None


def test_safety_multilingual_and_categories():
    """中文安全词 + 多类别命中"""
    from app.experts.safety_gate import scan_reviews
    r = scan_reviews(["玩具小零件，孩子差点窒息", "充电时漏电，有触电感觉"])
    assert r["incident_detected"] is True
    assert "choking_ingestion" in r["categories_hit"]
    assert "electrical" in r["categories_hit"]


def test_review_insights_includes_safety_alert(client):
    """/review-insights 集成：安全差评返回 safety_alert，普通差评为 None"""
    h = register_and_login(client, "safety1@test.com")
    r = client.post("/api/v1/products/review-insights", headers=h, json={
        "reviews": ["The toy charger overheated and melted the plug."]})
    assert r.status_code == 200
    alert = r.json()["safety_alert"]
    assert alert and alert["incident_detected"] is True
    # 普通差评 → safety_alert 为 None
    r2 = client.post("/api/v1/products/review-insights", headers=h, json={
        "reviews": ["Slow shipping, took three weeks."]})
    assert r2.json()["safety_alert"] is None


def test_exported_skill_data_in_sync():
    """开源 Skill 数据与引擎代码同步（防漂移）"""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    gpsr = json.loads((root / "skills" / "gpsr-compliance-checker" / "data"
                       / "gpsr_rules.json").read_text(encoding="utf-8"))
    from app.experts.gpsr import CE_RULES
    from app.experts.safety_gate import SAFETY_LEXICON
    assert len(gpsr["ce_categories"]) == len(CE_RULES)
    assert (sum(len(v) for v in gpsr["safety_incident_lexicon"].values())
            == sum(len(v) for v in SAFETY_LEXICON.values()))
    plats = json.loads((root / "skills" / "eu-marketplace-rules" / "data"
                        / "platforms.json").read_text(encoding="utf-8"))
    from app.experts.platform_registry import PLATFORMS
    assert set(plats["platforms"].keys()) == set(PLATFORMS.keys())
