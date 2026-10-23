"""
Rufus / iZi 语义搜索适配评分

背景：Amazon Rufus、Allegro iZi 等 AI 购物助手用「买家口语化提问」检索商品。
listing 若没有回答这些高频问题，在语义搜索时代等于隐形。

本模块（确定性规则，零 LLM 依赖）：
1. 从 title / bullets / description 中检测 8 类买家高频问题的回答信号
2. 输出 0-100 语义覆盖分 + 缺口清单（gaps），用于指导 listing 改写
"""
from typing import Dict, List

# 信号 → 买家问题（Rufus/iZi 会问的那种）
SIGNALS: List[Dict] = [
    {"key": "material", "weight": 15, "question": "它是什么材质做的？",
     "patterns": ["material", "stainless", "silicone", "cotton", "leather", "plastic",
                  "aluminum", "aluminium", "ceramic", "bamboo", "fabric", "steel"]},
    {"key": "how_to_use", "weight": 15, "question": "怎么用 / 适合什么场景？",
     "patterns": ["easy to", "perfect for", "ideal for", "suitable for", "how to",
                  "use for", "great for", "designed for", "portable", "rechargeable"]},
    {"key": "compatibility", "weight": 12, "question": "和我的设备/尺寸兼容吗？",
     "patterns": ["compatible", "fit", "fits", "universal", "works with", "for iphone",
                  "for android", "adjustable", "size"]},
    {"key": "safety", "weight": 12, "question": "安全吗？有认证吗？",
     "patterns": ["safe", "certified", "ce", "rohs", "en 71", "bpa", "non-toxic",
                  "warning", "safety"]},
    {"key": "warranty", "weight": 12, "question": "坏了怎么办？有保修/退货吗？",
     "patterns": ["warranty", "guarantee", "return", "refund", "replacement",
                  "12-month", "24-month", "lifetime", "after-sales"]},
    {"key": "specs", "weight": 12, "question": "具体参数（尺寸/容量/功率）是多少？",
     "patterns": ["mah", "watt", " mm", " cm", " inch", "oz", "ml", "liter", "capacity",
                  "voltage", "g "]},
    {"key": "audience", "weight": 11, "question": "适合谁用？（送礼/儿童/专业）",
     "patterns": ["for kids", "for children", "for adults", "for beginners", "gift",
                  "professional", "unisex", "men", "women", "family"]},
    {"key": "packaging", "weight": 11, "question": "包装里有什么？",
     "patterns": ["package includes", "in the box", "what you get", "comes with",
                  "includes", "accessories", " x1", " x2"]},
]


def score_semantics(title: str, bullet_texts: List[str], description: str) -> Dict:
    """返回 {score, answered:[{key,question}], gaps:[question,...]}"""
    text = (title + " " + " ".join(bullet_texts) + " " + description).lower()
    total_weight = sum(s["weight"] for s in SIGNALS)
    answered, gaps, score = [], [], 0.0
    for s in SIGNALS:
        if any(p in text for p in s["patterns"]):
            answered.append({"key": s["key"], "question": s["question"]})
            score += s["weight"]
        else:
            gaps.append(s["question"])
    # 已回答的给足信号分；覆盖 5 类以上再奖励
    bonus = 10.0 if len(answered) >= 5 else 0.0
    return {
        "score": round(min(score / total_weight * 90 + bonus, 100.0), 1),
        "answered": answered,
        "gaps": gaps,
    }
