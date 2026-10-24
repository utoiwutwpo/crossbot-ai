"""
Phase 1：Listing 仓库 + 每日定时体检 + 风险日报
"""
from tests.conftest import register_and_login


def _add_listing(client, headers, name="Kids Building Blocks Toy",
                 platform="amazon", title="", description="", sku="SKU-1"):
    r = client.post("/api/v1/listings", headers=headers, json={
        "sku": sku, "product_name": name, "platform": platform,
        "keywords": ["toy", "building block"], "title": title,
        "bullets": [], "description": description})
    assert r.status_code == 200, r.text
    return r.json()


def test_add_listing_runs_first_check(client):
    """添加 listing 立即体检：高风险 CE 类目缺欧代/警示语 → high + 硬风险项"""
    headers = register_and_login(client, "watch1@test.com")
    d = _add_listing(client, headers)
    w = d["listing"]
    assert w["risk_level"] == "high"
    assert w["risk_score"] < 100
    codes = [i["code"] for i in w["risk_items"]]
    assert "missing_eu_responsible" in codes
    assert "missing_local_warnings" in codes
    assert w["gpsr_block"]            # GPSR 合规块已生成
    assert d["first_check"]["after"] == "high"


def test_compliant_listing_scores_high(client):
    """写了欧代+警示语+说明书的 listing 风险显著下降"""
    headers = register_and_login(client, "watch2@test.com")
    d = _add_listing(
        client, headers, sku="OK-1", title="Wooden Building Blocks Toy",
        description="WARNING: Not suitable for children under 36 months. "
                    "Responsible Economic Operator: EU GmbH, Berlin, eu@example.com. "
                    "Model: BL-01. User manual included.")
    w = d["listing"]
    codes = [i["code"] for i in w["risk_items"]]
    assert "missing_eu_responsible" not in codes
    assert "missing_local_warnings" not in codes
    assert w["risk_level"] != "high" and w["risk_score"] >= 90


def test_watch_limit_free_plan(client):
    """free 套餐上限 5 条，第 6 条 402 引导升级"""
    headers = register_and_login(client, "watch3@test.com")
    for i in range(5):
        _add_listing(client, headers, sku=f"S-{i}",
                     name=f"Phone Case {i}", platform="amazon")
    r = client.post("/api/v1/listings", headers=headers, json={
        "product_name": "Extra Item", "platform": "amazon"})
    assert r.status_code == 402
    assert "升级" in r.json()["detail"]


def test_run_watch_generates_daily_report(client):
    """/watch/run 一轮体检 + 当天日报；listing 恶化时进入 new_risks"""
    headers = register_and_login(client, "watch4@test.com")
    # 先添加合规 listing（低风险）
    d0 = _add_listing(
        client, headers, sku="R-1", title="Bluetooth Speaker Mini",
        description="WARNING: read manual. Responsible Economic Operator: "
                    "EU GmbH, Berlin. Model SP-9. Achtung: Warnung included.")
    assert d0["listing"]["risk_level"] != "high"
    # 首轮日报：已有等级 → 无恶化
    r = client.post("/api/v1/watch/run", headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["total_listings"] == 1
    assert d["high_count"] == 0
    assert d["new_risks"] == []
    # 用户把文案改坏（清空描述回贴残缺版）→ 更新后重检 → 恶化
    r = client.put(f"/api/v1/listings/{d0['listing']['id']}", headers=headers,
                   json={"description": "", "title": ""})
    assert r.status_code == 200
    assert r.json()["listing"]["risk_level"] == "high"
    r2 = client.post("/api/v1/watch/run", headers=headers)
    d2 = r2.json()
    assert d2["high_count"] == 1
    assert len(d2["new_risks"]) == 1 and d2["new_risks"][0]["to"] == "high"
    # latest 接口
    r3 = client.get("/api/v1/watch/report/latest", headers=headers)
    assert r3.json()["report"]["report_date"] == d2["report_date"]


def test_listing_detail_recheck_delete(client):
    headers = register_and_login(client, "watch5@test.com")
    d = _add_listing(client, headers, sku="D-1", name="Bluetooth Speaker")
    wid = d["listing"]["id"]
    # 详情
    r = client.get(f"/api/v1/listings/{wid}", headers=headers)
    assert r.status_code == 200
    codes = [i["code"] for i in r.json()["risk_items"]]
    assert "missing_eu_responsible" in codes      # 无线电类目高风险：缺欧代
    # 重检
    r = client.post(f"/api/v1/listings/{wid}/recheck", headers=headers)
    assert r.status_code == 200
    assert r.json()["listing"]["id"] == wid
    # 越权访问他人 listing → 404
    other = register_and_login(client, "watch5b@test.com")
    r = client.get(f"/api/v1/listings/{wid}", headers=other)
    assert r.status_code == 404
    # 删除
    r = client.delete(f"/api/v1/listings/{wid}", headers=headers)
    assert r.status_code == 200
    assert client.get(f"/api/v1/listings/{wid}", headers=headers).status_code == 404


def test_scheduler_daily_job(client):
    """调度器 job 函数直接调用：对全库跑一轮，日报落地"""
    headers = register_and_login(client, "watch6@test.com")
    _add_listing(client, headers, sku="J-1", name="USB Charger",
                 platform="amazon_us")
    from app.scheduler import daily_watch_job
    summary = daily_watch_job()
    assert summary["failed"] == 0
    assert summary["users_processed"] >= 1
    r = client.get("/api/v1/watch/report/latest", headers=headers)
    assert r.status_code == 200
    rep = r.json()["report"]
    assert rep["total_listings"] == 1
    assert rep["email_sent"] is False   # 测试环境无 SMTP
