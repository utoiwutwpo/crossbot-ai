"""
Rufus/iZi 语义搜索适配评分测试
"""
from app.experts.semantics import score_semantics


def test_full_listing_scores_high():
    r = score_semantics(
        "Stainless Steel Smart Water Bottle 750ml for Kids",
        ["Perfect for school, BPA free and CE certified",
         "Comes with 12-month warranty and free replacement",
         "Package includes bottle x1 and brush x2"],
        "Compatible with most cup holders. 750ml capacity, 21 cm tall. Great gift for family.")
    assert r["score"] >= 70
    assert len(r["gaps"]) <= 3


def test_sparse_listing_flags_gaps():
    r = score_semantics("Nice Water Bottle", [], "A bottle for water.")
    assert r["score"] < 40
    assert any("材质" in g for g in r["gaps"])
    assert any("保修" in g for g in r["gaps"])


def test_description_api_returns_semantic_fields(client):
    from tests.conftest import register_and_login
    headers = register_and_login(client, "sem@test.com")
    r = client.post("/api/v1/products/descriptions/generate", headers=headers,
                    json={"product_name": "Stainless Steel Water Bottle for Kids",
                          "keywords": ["bottle", "gift"], "platform": "amazon"})
    assert r.status_code == 200
    d = r.json()
    assert d["semantic_score"] is not None
    assert isinstance(d["semantic_gaps"], list)
