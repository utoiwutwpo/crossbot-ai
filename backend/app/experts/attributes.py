"""
平台属性树引擎 — 各平台类目必填参数校验（对齐 Marqetir「首过率」卖点）

差异化逻辑：listing 文案再好，类目结构化属性缺失/填错 → 平台审核直接驳回。
本模块做三件事：
1. required_attributes()：按平台 + 商品类目给出必填/推荐属性树
2. validate_attributes()：校验卖家已填属性 → 缺失/格式错误/硬阻断清单
3. completeness()：属性完整度评分（计入 listing 质量分）

⚠️ 属性字段为工程默认值（基于各平台卖家中心公开文档的常见要求），
平台会不定期调整，上架前以卖家中心最新类目模板为准。
"""
import re
from typing import Dict, List, Optional

# ---------- 商品类目自动识别（关键词 → 类目） ----------
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "electronics": [
        "bluetooth", "wireless", "charger", "camera", "smart", "monitor", "speaker",
        "耳机", "充电", "摄像", "智能", "电子", "电子表", "watch", "phone", "tablet",
    ],
    "toys": [
        "toy", "blocks", "puzzle", "kids", "children", "doll", "lego", "plush",
        "玩具", "积木", "拼图", "儿童", "娃娃", "毛绒",
    ],
    "home": [
        "kitchen", "lamp", "storage", "furniture", "bed", "chair", "curtain",
        "厨房", "灯", "收纳", "家具", "床", "椅", "窗帘", "home",
    ],
    "fashion": [
        "shirt", "dress", "shoes", "jacket", "bag", "backpack", "socks", "hat",
        "衬衫", "裙", "鞋", "外套", "包", "袜", "帽", "apparel",
    ],
    "beauty": [
        "cream", "serum", "shampoo", "cosmetic", "makeup", "skin", "lotion",
        "面霜", "精华", "洗发", "化妆", "护肤", "美妆",
    ],
}


def detect_category(keywords: List[str], product_name: str = "") -> str:
    text = (product_name + " " + " ".join(keywords)).lower()
    best, hits = "generic", 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        n = sum(1 for k in kws if k in text)
        if n > hits:
            best, hits = cat, n
    return best


# ---------- 属性定义 ----------
# type: str / int / ean13 / enum；required: hard(缺失驳回) / soft(建议) / False
def _attr(key, label, type_="str", required=False, example="", help_="", enum=None):
    return {
        "key": key, "label": label, "type": type_, "required": required,
        "example": example, "help": help_, "enum": enum or [],
    }


def _tree(platform: str) -> List[dict]:
    """各平台属性树。required: 'hard' 缺失即驳回 / 'soft' 建议填写。"""
    common_brand = _attr("brand", "品牌 Brand", required="hard", example="Anker",
                         help_="无品牌填 Generic/无品牌（平台可能限制展示）")
    attrs = {
        # Allegro：参数（Parametry）缺失是波兰站审核驳回首因
        "allegro": [
            common_brand,
            _attr("ean", "EAN/GTIN 条码", "ean13", required="hard", example="5901234123457",
                  help_="Allegro 大多数类目强制 EAN；无条码需申请豁免"),
            _attr("condition", "商品状态 Stan", required="hard", example="new",
                  enum=["new", "used", "refurbished"], help_="new/used/refurbished"),
            _attr("model", "型号 Model", required="soft", example="BX-200"),
            _attr("material", "材质 Materiał", required="soft", example="ABS + silicone",
                  help_="home/fashion/toys 类目强烈建议"),
            _attr("warranty", "保修（月）", "int", required="soft", example="24"),
        ],
        # eMAG：品牌/家族/型号 + 保修月数是特点字段
        "emag": [
            common_brand,
            _attr("family", "产品家族 Family", required="hard", example="SleepMask Series",
                  help_="同系列多变体必须同 family 才能合并变体"),
            _attr("part_number", "厂商料号 Part Number", required="hard", example="SSM-001"),
            _attr("warranty_months", "保修月数 Garanție", "int", required="hard", example="24",
                  help_="eMAG 强制整数值，缺驳回"),
            _attr("ean", "EAN/GTIN 条码", "ean13", required="soft", example="5941234123457"),
            _attr("material", "材质 Material", required="soft", example="Cotton"),
        ],
        # TikTok Shop：合规导向（认证/资质）
        "tiktok": [
            common_brand,
            _attr("sku", "商家编码 SKU", required="hard", example="TT-SSM-001-Black"),
            _attr("certification", "类目资质 Certification", required="soft", example="CE/RED 证书编号",
                  help_="电子/美妆/母婴类目欧盟站点须上传资质证书，缺失会被下架"),
            _attr("material", "材质", required="soft", example="ABS"),
            _attr("gtin", "GTIN/EAN", "ean13", required="soft", example="0691234567890"),
        ],
        # Kaufland Global：德区严格，EAN + 制造商
        "kaufland": [
            common_brand,
            _attr("manufacturer", "制造商 Hersteller", required="hard", example="Shenzhen X Ltd.",
                  help_="与 GPSR 欧代/制造商信息一致"),
            _attr("ean", "EAN/GTIN 条码", "ean13", required="hard", example="4011234123457"),
            _attr("safety_warning", "安全警示（德语）", required="soft", example="Nicht für Kinder unter 3 Jahren",
                  help_="toys/beauty 类目建议与 GPSR 警示语一致"),
            _attr("model", "型号 Modell", required="soft", example="KL-330"),
        ],
        # bol.com：EAN 是硬钥匙，缺了产品根本建不了
        "bol": [
            _attr("ean", "EAN 条码", "ean13", required="hard", example="8711234123457",
                  help_="bol.com 用 EAN 作为产品唯一键，缺失直接无法创建 offer"),
            common_brand,
            _attr("model", "型号", required="soft", example="BL-77"),
            _attr("packaging_language", "包装语言", required="soft", example="nl",
                  enum=["nl", "fr", "en"], help_="NL/BE 站建议 nl 或 fr"),
        ],
        # Zalando：EAN + 材质成分 + 尺码网格是硬钥匙，缺了商品直接拒收
        "zalando": [
            _attr("ean", "EAN/GTIN 条码", "ean13", required="hard", example="8711234123457",
                  help_="Zalando 用 EAN 作为商品唯一键，缺失无法创建"),
            common_brand,
            _attr("material_composition", "材质成分", required="hard",
                  example="80% Cotton, 20% Polyester",
                  help_="纺织品类目强制 EU 1007/2011 纤维成分标签"),
            _attr("size_grid", "尺码网格", required="hard", example="EU 36-46 / US 6-16",
                  help_="时尚类目必须提交完整尺码网格（size grid）"),
            _attr("care_instructions", "洗涤/护理说明", required="soft",
                  example="Machine wash 30°C", help_="德区消费者对护理说明极敏感，建议填写"),
            _attr("model", "款式/型号", required="soft", example="ZL-2210"),
        ],
    }
    return attrs.get(platform, [
        common_brand,
        _attr("model", "型号 Model", required="soft", example="M1"),
        _attr("material", "材质 Material", required="soft", example="ABS"),
        _attr("ean", "EAN/GTIN 条码", "ean13", required="soft", example="6901234123456"),
    ])


# ---------- 公开 API ----------

def required_attributes(platform: str, category: str = "generic") -> List[dict]:
    """平台属性树（可按类目过滤的预留参数位）。"""
    return _tree(platform)


def validate_attributes(
    platform: str,
    provided: Dict[str, str],
    category: str = "generic",
) -> dict:
    """校验已填属性 → 缺失 / 格式错误 / 硬阻断 + 完整度。"""
    tree = required_attributes(platform, category)
    missing, invalid, blockers = [], [], []
    filled = 0
    total_required = 0

    for a in tree:
        val = (provided.get(a["key"]) or "").strip()
        is_required = a["required"] == "hard"
        if is_required:
            total_required += 1
        if not val:
            item = {"key": a["key"], "label": a["label"], "help": a["help"],
                    "example": a["example"]}
            if is_required:
                missing.append(item)
                blockers.append(f"缺少必填属性 {a['label']}（{a['key']}）—— 审核大概率驳回")
            else:
                missing.append({**item, "severity": "soft"})
            continue
        # 有值 → 类型校验
        ok, err = _check_type(val, a)
        if not ok:
            invalid.append({"key": a["key"], "label": a["label"], "value": val, "error": err})
            if is_required:
                blockers.append(f"必填属性 {a['label']} 格式错误：{err}")
        else:
            filled += 1

    hard_total = total_required if total_required else 1
    hard_filled = sum(
        1 for a in tree
        if a["required"] == "hard" and (provided.get(a["key"]) or "").strip()
    )
    soft_total = len(tree) - hard_total
    soft_filled = sum(
        1 for a in tree
        if a["required"] != "hard" and (provided.get(a["key"]) or "").strip()
    )
    completeness = round(
        (hard_filled / hard_total) * 70 + (soft_filled / soft_total if soft_total else 1) * 30, 1
    )
    return {
        "platform": platform,
        "category": category,
        "missing": missing,
        "invalid": invalid,
        "blockers": blockers,
        "ready_to_list": len(blockers) == 0,
        "completeness": completeness,
        "checked_total": len(tree),
    }


def _check_type(val: str, attr_def: dict):
    t = attr_def["type"]
    if t == "ean13":
        if not re.fullmatch(r"\d{13}", val):
            return False, "EAN 必须是 13 位数字"
        # EAN-13 校验位
        digits = [int(d) for d in val]
        checksum = (10 - sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:12])) % 10) % 10
        if checksum != digits[12]:
            return False, "EAN 校验位不合法（疑似杜撰条码，平台会驳回）"
        return True, ""
    if t == "int":
        try:
            int(val)
            return True, ""
        except ValueError:
            return False, "必须为整数"
    if t == "enum":
        if val.lower() in [e.lower() for e in attr_def["enum"]]:
            return True, ""
        return False, f"可选值：{' / '.join(attr_def['enum'])}"
    return True, ""
