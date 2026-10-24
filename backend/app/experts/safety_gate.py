"""
GPSR 安全事件预警 — EU 2023/988 强制事故上报闭环

法规要点（GPSR Art.35 / Safety Gate）：
- 制造商与欧代「知晓」严重安全事故或产品缺陷后，必须在 15 天内向相关
  欧盟成员国市场监督机构上报（严重风险走 EU Safety Gate 门户）。
- 「知晓」的认定早于多数卖家预期：买家投诉、退货中发现的与安全相关的缺陷、
  社交媒体上的伤害报告，都可能构成「知晓」并触发 15 天计时。
- Safety Gate 数据库对全欧盟执法机构可见——德国一单上报，法/荷/西立即知悉。

本模块：扫描差评文本中的安全词 → 命中即输出 incident alert +
15 天行动清单。纯确定性规则，零 LLM 依赖，可挂进 7x24 监控。
"""
import re
from typing import Dict, List

# 安全词库（按伤害类别分组）— 命中任一即触发人工复核
SAFETY_LEXICON: Dict[str, List[str]] = {
    "fire_thermal": [
        "fire", "caught fire", "flames", "burn", "burned", "burnt",
        "smoke", "overheated", "overheating", "over heat", "melted",
        "exploded", "爆炸", "起火", "烧", "冒烟", "过热", "融化",
    ],
    "electrical": [
        "electric shock", "shock", "sparking", "sparked", "short circuit",
        "electrocut", "漏电", "触电", "短路", "电人",
    ],
    "choking_ingestion": [
        "choke", "choking", "choked", "swallow", "swallowed", "ingest",
        "ingested", "mouthed", "窒息", "误吞", "吞", "卡喉",
    ],
    "mechanical": [
        "cut", "laceration", "bleeding", "sharp edge", "sharp corner",
        "pinched", "finger trapped", "broke apart", "shattered",
        "割伤", "划伤", "割破", "破碎", "夹伤", "碎片",
    ],
    "chemical_allergy": [
        "allergic", "allergic reaction", "rash", "itching skin", "burn skin",
        "poison", "toxic", "poisoning", "ingested chemical",
        "过敏", "红疹", "皮疹", "中毒", "毒性",
    ],
}

# 安全词 > 缺陷聚类 > 1星突增 > 孤立差评（severity 参考 pangolinfo 分层 + GPSR 义务）
_SEVERITY = "safety_critical"

_ACTION_STEPS = [
    "① 立即评估是否停售/下架该 listing（安全风险下平台有权即时下架，主动停售可控得多）",
    "② 保留实物样品、买家沟通记录、差评截图——技术文件的一部分",
    "③ 判定事故严重性：有人身伤害 → 15 天内经 EU Safety Gate 门户上报；"
    "仅缺陷无伤害 → 上报相关成员国市场监督机构",
    "④ 通知你的欧盟授权代表（欧代）——上报义务主体是制造商与欧代",
    "⑤ 复核技术文件与 DoC 符合性声明：引用的标准版本是否过期（这是最高频的失败点）",
    "⑥ 全欧盟可见：一次上报即进入 Safety Gate 数据库，所有成员国执法机构同步知悉——"
    "第一时间把同批次风险产品从其他市场撤下",
]

_DEADLINE_NOTE = (
    "GPSR (EU) 2023/988 Art.35：制造商/欧代「知晓」严重事故后 15 日内必须上报。"
    "「知晓」从卖家看到差评/退货缺陷/伤害报告那一刻起计时，不是从事故发生日起计时。")


def scan_reviews(reviews: List[str]) -> Dict:
    """扫描评价文本中的安全词。命中 → incident_detected=True + 行动清单。

    纯确定性规则；宁可误报也不漏报（安全事件漏报的代价是执法处罚+全渠道下架）。
    """
    hits: List[Dict] = []
    for idx, review in enumerate(reviews):
        low = review.lower()
        for category, words in SAFETY_LEXICON.items():
            for w in words:
                if w in low:
                    hits.append({
                        "word": w, "category": category,
                        "review_index": idx,
                        "excerpt": review[:120],
                    })
    detected = bool(hits)
    return {
        "incident_detected": detected,
        "severity": _SEVERITY if detected else None,
        "hits": hits[:20],  # 上限防炸
        "categories_hit": sorted({h["category"] for h in hits}),
        "deadline_note": _DEADLINE_NOTE if detected else None,
        "action_steps": _ACTION_STEPS if detected else None,
        "data_source": "safety_lexicon_scan",   # 如实标注判定来源
    }


def safety_keywords_hint() -> List[str]:
    """给前端的提示词（展示前 12 个高频安全词）"""
    flat = [w for ws in SAFETY_LEXICON.values() for w in ws if len(w) > 2]
    return flat[:12]
