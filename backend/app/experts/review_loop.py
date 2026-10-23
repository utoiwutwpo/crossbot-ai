"""
Review → Listing 闭环 — 差评反向改写五点描述

逻辑：粘贴差评（可多条）→ 主题/情绪提取 → 定位 listing 缺口 →
输出可直接粘贴的五点描述改写建议 + 优先级排序。
对应竞品扫描报告第 4 押注点（行业基本空白）。
"""
import re
from typing import Dict, List, Optional

from ..schemas import BulletPoint, ReviewInsightRequest, ReviewInsightResponse

# 主题识别：主题 → (关键词, 严重度基线, 修复模板)
THEMES: Dict[str, dict] = {
    "shipping": {
        "kws": ["slow shipping", "took weeks", "late", "delivery", "never arrived",
                "物流", "发货慢", "迟迟不到", "很久才到"],
        "severity": "medium",
        "fix_heading": "Fast & Tracked Shipping",
        "fix_content": ("Ships within 24 hours with full tracking. "
                        "Delivery in 5-8 business days — you can follow every step."),
        "listing_action": "五点描述第 1 点补充发货时效与追踪承诺，压制『物流慢』预期差",
    },
    "size_fit": {
        "kws": ["too small", "too large", "runs small", "size", "doesn't fit",
                "尺寸", "太小", "太大", "不合身"],
        "severity": "high",
        "fix_heading": "True-to-Size, Double-Checked",
        "fix_content": ("Detailed size chart with real measurements (not just S/M/L). "
                        "If between sizes, we recommend sizing up for the best fit."),
        "listing_action": "详情页加真实测量尺寸表；标题/五点写入『True to Size + 参考建议』",
    },
    "quality": {
        "kws": ["broke", "broken", "cheap", "flimsy", "stopped working", "fell apart",
                "坏了", "质量差", "脆弱", "用几天就"],
        "severity": "high",
        "fix_heading": "Built to Last — Tested",
        "fix_content": ("Made from reinforced {material} and stress-tested for 10,000+ cycles. "
                        "Backed by a 24-month replacement warranty."),
        "listing_action": "五点增加『材质+测试次数+保修』三要素，直接反驳『廉价易坏』认知",
    },
    "battery": {
        "kws": ["battery", "doesn't hold charge", "dies quickly", "charging",
                "电池", "不耐用", "掉电快"],
        "severity": "high",
        "fix_heading": "Real-World Battery Life",
        "fix_content": ("{battery_life} on a single charge under normal use — "
                        "verified by third-party testing, not lab ideal conditions."),
        "listing_action": "电池续航写实测值并标注测试条件，避免『实验室续航』落差差评",
    },
    "instructions": {
        "kws": ["no instructions", "confusing", "hard to set up", "manual",
                "没说明书", "不会用", "看不懂", "组装"],
        "severity": "medium",
        "fix_heading": "Setup in 3 Minutes",
        "fix_content": ("Includes step-by-step illustrated guide (EN/DE/FR) and a QR code "
                        "to a 60-second setup video — no guesswork needed."),
        "listing_action": "五点声明多语言图示说明书 + 视频教程链接，详情页嵌入安装图",
    },
    "compatibility": {
        "kws": ["doesn't fit my", "not compatible", "doesn't work with", "compatib",
                "不兼容", "不适配"],
        "severity": "high",
        "fix_heading": "Check Compatibility in 10 Seconds",
        "fix_content": ("Works with {compat_list}. Not sure? Message us your model number "
                        "and we'll confirm before you order."),
        "listing_action": "兼容机型/型号清单写入标题尾部 + 五点第 2 点，前置过滤误购",
    },
    "smell": {
        "kws": ["smell", "odor", "chemical smell", "stink",
                "异味", "味道大", "刺鼻"],
        "severity": "medium",
        "fix_heading": "Odor-Free Materials",
        "fix_content": ("Made from food-grade, odor-free {material}. Aired and inspected "
                        "before packing — safe out of the box."),
        "listing_action": "材质说明强调食品级/无异味认证；若确有异味投诉需排查供应商",
    },
    "expectation_gap": {
        "kws": ["not as described", "misleading", "picture looks", "smaller than",
                "与描述不符", "图片与实物", "货不对板"],
        "severity": "high",
        "fix_heading": "What You See Is What Arrives",
        "fix_content": ("Photos taken of the actual product with real dimensions shown. "
                        "No CGI renders, no exaggerated angles."),
        "listing_action": "⚠️ 高危信号：主图/详情图与实物差距过大，立即更换实物图，"
                          "否则差评+退货率会拖垮 listing 排名",
    },
}


class ReviewLoopExpert:
    name = "review_loop"
    description = "差评 → listing 改写建议"

    def analyze(self, req: ReviewInsightRequest) -> ReviewInsightResponse:
        text = " | ".join(req.reviews).lower()
        rating = req.rating
        themes_hit: List[dict] = []

        for theme, cfg in THEMES.items():
            evidence = [kw for kw in cfg["kws"] if kw in text]
            if not evidence:
                continue
            severity = cfg["severity"]
            if rating is not None and rating <= 2:
                # 一二星差评：主题严重度整体上调
                severity = "critical" if severity == "high" else "high"
            fix_content = cfg["fix_content"]
            if "{material}" in fix_content:
                fix_content = fix_content.replace(
                    "{material}", req.material or "premium materials")
            if "{battery_life}" in fix_content:
                fix_content = fix_content.replace(
                    "{battery_life}", req.battery_life or "8-10 hours")
            if "{compat_list}" in fix_content:
                fix_content = fix_content.replace(
                    "{compat_list}", req.compatibility or "major models (see list)")
            themes_hit.append({
                "theme": theme,
                "evidence_keywords": evidence[:5],
                "severity": severity,
                "listing_action": cfg["listing_action"],
                "bullet_fix": {"heading": cfg["fix_heading"], "content": fix_content},
            })

        # 严重度排序：critical > high > medium > low
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        themes_hit.sort(key=lambda t: order.get(t["severity"], 9))

        total = len(req.reviews)
        if themes_hit:
            summary = (
                f"分析 {total} 条评价：命中 {len(themes_hit)} 个可修复主题，"
                f"最高优先级是「{themes_hit[0]['theme']}」（{themes_hit[0]['severity']}）。"
                f"优先落实第一条 listing 行动，其余按序处理。"
                if total > 1 else
                f"命中 {len(themes_hit)} 个可修复主题，最高优先级「{themes_hit[0]['theme']}」。"
            )
        else:
            summary = ("未命中已知差评主题。若为好评，建议把用户自发的使用场景关键词"
                       "沉淀进五点描述与后台搜索词。")

        return ReviewInsightResponse(
            reviews_analyzed=total,
            sentiment=("very_negative" if (rating is not None and rating <= 2)
                       else "negative"),
            themes=themes_hit,
            improved_bullets=[
                BulletPoint(**t["bullet_fix"]) for t in themes_hit
            ],
            summary=summary,
        )
