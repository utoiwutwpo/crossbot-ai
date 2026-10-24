"""
Listing 监控引擎（7x24 自动体检的核心）
纯确定性规则：GPSR 合规 + 平台字数规则 + 必备要素，零 LLM 成本 → 可全量每日扫描。

evaluate_listing() 输出：
- risk_level: low / medium / high
- risk_score: 0-100（100 = 无发现风险）
- risk_items: [{severity, code, message}]
- fix_hints: 修复建议（与 risk_items 一一对应）
- gpsr_block: 直接可粘贴的 GPSR 合规块（来自 gpsr 引擎）
"""
import re
from typing import Dict, List

from .gpsr import check as gpsr_check
from .platform_registry import platform_config

# listing 文本中被视为"已有欧代信息"的标记
_EU_RESPONSIBLE_RE = re.compile(
    r"responsible\s+economic\s+operator|economic\s+operator|eu\s+responsible"
    r"|authorized\s+representative|authorised\s+representative"
    r"|欧代|欧盟授权代表|europ(?:ä|ae)ischer\s+bevollm", re.I)

# 被视为"已有说明书"的标记
_MANUAL_RE = re.compile(r"manual|instruction|user\s*guide|handbuch|notice|说明书|anleitung", re.I)

# 被视为"已有型号/批次"的标记
_MODEL_RE = re.compile(r"model|batch|serial|asin|ean|型号|批次|artikel", re.I)


def evaluate_listing(product_name: str, keywords: List[str], platform: str,
                     title: str = "", bullets: List[str] = None,
                     description: str = "") -> Dict:
    """对一条 listing 快照做确定性合规体检"""
    bullets = bullets or []
    cfg = platform_config(platform)
    items: List[Dict] = []
    hints: List[Dict] = []

    def add(severity: str, code: str, message: str, fix: str):
        items.append({"severity": severity, "code": code, "message": message})
        hints.append({"code": code, "fix": fix})

    # ---- 1. 平台硬规则：标题长度 ----
    title_max = cfg.get("title_max", 200)
    if title and len(title) > title_max:
        add("high", "title_too_long",
            f"标题 {len(title)} 字符，超过 {cfg['display']} 上限 {title_max}，上架时会被截断或拒绝",
            f"压缩到 {title_max} 字符内：保留核心关键词，删除堆砌修饰词")

    # ---- 2. GPSR 体检（确定性）----
    g = gpsr_check(product_name, keywords, platform)
    full_text = " ".join([product_name, title, " ".join(bullets), description or ""])

    if g["ce_required"]:
        if not _EU_RESPONSIBLE_RE.search(full_text):
            add("high", "missing_eu_responsible",
                f"识别为高风险类目（{g['matched_categories']}），listing 未含欧盟责任人（欧代）信息，"
                "EU 2023/988 强制要求，平台会下架",
                "在描述或合规块中加入欧代名称+地址+邮箱（使用下方 GPSR 合规块即可）")
        if not _MODEL_RE.search(full_text):
            add("medium", "missing_product_id",
                "未检测到型号/批次/序列号等产品追溯标识（GPSR Art.9）",
                "在标题或描述中补充 Model/Batch 标识")
        if not _MANUAL_RE.search(full_text):
            add("medium", "missing_manual",
                "CE 类目未检测到当地语言说明书信息",
                "补充 'User manual available in [语言]' 或上传说明书文件")
        # 警示语：高风险类目须含目标市场语言安全警示（宽松判定：任一必需语言关键词）
        if not _warnings_present(full_text, g["required_languages"]):
            add("high", "missing_local_warnings",
                f"未检测到目标市场语言安全警示（需要：{', '.join(g['required_languages'])}）",
                "把下方 GPSR 合规块中的当地语言警示语粘贴进 listing")
    else:
        if not _EU_RESPONSIBLE_RE.search(full_text):
            add("medium", "missing_eu_responsible_soft",
                "未识别到受监管类目，但 GPSR Art.9 基本义务仍要求欧代+安全信息",
                "建议同样加入 GPSR 合规块，防患于未然")

    # ---- 3. 内容完整度 ----
    if not description:
        add("medium", "missing_description", "缺少产品详情描述", "生成完整描述并补充")
    if len(bullets) < 3:
        add("low", "few_bullets",
            f"五点描述仅 {len(bullets)} 条（建议 5 条）", "补齐卖点五点描述")

    # ---- 汇总 ----
    high_n = sum(1 for i in items if i["severity"] == "high")
    med_n = sum(1 for i in items if i["severity"] == "medium")
    low_n = sum(1 for i in items if i["severity"] == "low")
    score = max(0, 100 - 25 * high_n - 10 * med_n - 3 * low_n)
    level = "low" if high_n == 0 and med_n <= 1 else ("medium" if high_n == 0 else "high")

    return {
        "risk_level": level,
        "risk_score": score,
        "risk_items": items,
        "fix_hints": hints,
        "matched_categories": g["matched_categories"],
        "ce_required": g["ce_required"],
        "required_languages": g["required_languages"],
        "gpsr_block": g["gpsr_block"],
    }


def _warnings_present(text: str, languages: List[str]) -> bool:
    """宽松判定：文本中是否已有主要欧洲语言的警示语标记"""
    markers = {
        "en": r"warning|caution", "de": r"achtung|warnung", "fr": r"avertissement",
        "es": r"advertencia", "it": r"avvertenza", "pl": r"ostrzeżenie",
        "ro": r"avertizare", "nl": r"waarschuwing", "sv": r"varning",
        "cs": r"pozor|varování", "hu": r"figyelem", "bg": r"внимание",
    }
    # 任一目标语言的警示标记出现即认为有本地化警示（至少覆盖一种市场）
    for lang in languages:
        pat = markers.get(lang)
        if pat and re.search(pat, text, re.I):
            return True
    return False
