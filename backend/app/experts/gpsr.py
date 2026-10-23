"""
GPSR 合规引擎 — General Product Safety Regulation (EU) 2023/988
2024-12-13 起强制执行：缺欧盟责任人/当地语言警示语的 listing 会被平台下架。

能力（纯确定性规则，无需 LLM 即可工作）：
1. 品类识别：从产品名/关键词推断是否属于 CE 标识类目（玩具/电子/无线电/PPE/母婴…）
2. 语言要求：按平台覆盖国家计算警示语必需语言
3. 合规体检：7 项法定检查清单（manufacturer / 欧代 / 产品标识 / CE 标识 / 警示语 / 图片 / 说明书）
4. GPSR 合规块：可直接粘贴进 listing 的合规文本（当地语言警示语 + 欧代占位）

⚠️ 免责声明：本模块输出为工程辅助建议，不能替代法律意见；
具体类目适用指令以欧盟官方文本与认证机构意见为准。
"""
import re
from typing import Dict, List, Optional


# ---------- CE 类目规则库 ----------
# keywords: 触发词（对 product_name + keywords 做小写子串匹配）
CE_RULES: List[Dict] = [
    {
        "category": "toys",
        "label": "玩具",
        "keywords": ["toy", "doll", "puzzle", "plush", "lego", "building block",
                     "spielzeug", "jouet", "giocattolo", "juguete", "zabawka",
                     "rc car", "teddy", "figurine toy", "kids game", "儿童", "玩具"],
        "directives": ["2009/48/EC Toy Safety Directive (EN 71-1/2/3)"],
        "risk": "high",
        "extra": "必须标注适用年龄；含小零件须有窒息警示（36 个月以下不适用）",
        "warnings": {
            "en": "WARNING: Not suitable for children under 36 months. Small parts. Choking hazard.",
            "de": "ACHTUNG: Nicht geeignet für Kinder unter 36 Monaten. Kleinteile. Erstickungsgefahr.",
            "fr": "AVERTISSEMENT ! Ne convient pas aux enfants de moins de 36 mois. Petits éléments. Danger d'étouffement.",
            "es": "ADVERTENCIA: No adecuado para menores de 36 meses. Piezas pequeñas. Peligro de asfixia.",
            "it": "AVVERTENZA: Non adatto a bambini di età inferiore a 36 mesi. Parti piccole. Rischio di soffocamento.",
            "pl": "OSTRZEŻENIE: Nieodpowiednie dla dzieci poniżej 36 miesięcy. Małe części. Ryzyko zadławienia.",
            "ro": "AVERTIZARE: Nu este potrivit pentru copiii sub 36 de luni. Piese mici. Pericol de sufocare.",
        },
    },
    {
        "category": "radio_equipment",
        "label": "无线电设备",
        "keywords": ["bluetooth", "wifi", "wi-fi", "wireless", "smart", "tracker",
                     "gps", "remote control", "4g", "5g", "nfc", "蓝牙", "无线"],
        "directives": ["2014/53/EU Radio Equipment Directive (RED)"],
        "risk": "high",
        "extra": "须声明频段与最大发射功率；SRD/蓝牙模块可用 RED 符合性声明",
        "warnings": {
            "en": "This device operates in compliance with EU radio spectrum regulations (2014/53/EU). Frequency band and max transmit power stated in the user manual.",
            "de": "Dieses Gerät entspricht den EU-Funkbestimmungen (2014/53/EU). Frequenzband und maximale Sendeleistung stehen in der Bedienungsanleitung.",
            "fr": "Cet appareil est conforme à la réglementation radioélectrique de l'UE (2014/53/EU). Bande de fréquences et puissance maximale indiquées dans le manuel.",
            "es": "Este dispositivo cumple la normativa de radio de la UE (2014/53/EU). Banda de frecuencia y potencia máxima indicadas en el manual.",
            "it": "Questo dispositivo è conforme alla normativa radio UE (2014/53/EU). Banda di frequenza e potenza massima indicate nel manuale.",
            "pl": "Urządzenie jest zgodne z przepisami radiowymi UE (2014/53/EU). Pasmo częstotliwości i maksymalna moc podano w instrukcji.",
            "ro": "Acest dispozitiv respectă reglementările radio UE (2014/53/EU). Banda de frecvență și puterea maximă sunt indicate în manual.",
        },
    },
    {
        "category": "electronics",
        "label": "电气电子",
        "keywords": ["charger", "usb", "adapter", "cable", "earbud", "headphone",
                     "speaker", "lamp", "led", "battery", "power bank", "plug",
                     "electronic", "electric", "mask", "heater", "fan", "充电",
                     "电子", "灯"],
        "directives": ["2014/35/EU Low Voltage Directive (LVD)",
                       "2014/30/EU EMC Directive",
                       "2011/65/EU RoHS"],
        "risk": "high",
        "extra": "插头须符合目标国制式（DE/FR 为 Schuko，IT 为 CEI 23-50）；含电池须有 WEEE/电池回收标识",
        "warnings": {
            "en": "Electrical safety: do not immerse in water; indoor use only unless stated. WEEE: dispose of at designated collection points, not household waste.",
            "de": "Elektrische Sicherheit: nicht in Wasser tauchen; nur für Innenbereiche, sofern nicht anders angegeben. WEEE: Bei Sammelstellen entsorgen, nicht in den Hausmüll.",
            "fr": "Sécurité électrique : ne pas immerger dans l'eau ; usage intérieur sauf indication contraire. DEEE : à déposer en point de collecte, pas aux ordures ménagères.",
            "es": "Seguridad eléctrica: no sumergir en agua; solo uso interior salvo indicación. RAEE: depositar en punto de limpieza, no en basura doméstica.",
            "it": "Sicurezza elettrica: non immergere in acqua; solo uso interno salvo indicazione. RAEE: conferire presso i punti di raccolta, non nei rifiuti domestici.",
            "pl": "Bezpieczeństwo elektryczne: nie zanurzać w wodzie; tylko do użytku wewnętrznego, chyba że wskazano inaczej. Zużyty sprzęt usuwać do punktów zbiórki, nie do odpadów domowych.",
            "ro": "Siguranță electrică: nu se scufundă în apă; doar uz interior, dacă nu se indică altfel. EEE uzat: predat la punctele de colectare, nu la deșeurile menajere.",
        },
    },
    {
        "category": "ppe",
        "label": "个人防护装备",
        "keywords": ["helmet", "glove", "goggle", "respirator", "safety vest",
                     "earplug", "safety shoe", "knee pad", "头盔", "防护"],
        "directives": ["2016/425 Personal Protective Equipment Regulation (PPE)"],
        "risk": "high",
        "extra": "须标注防护级别与标准号（如 EN 166）；用户说明书为强制文件",
        "warnings": {
            "en": "PPE: read the user instructions before use. Protection level and applicable standard (e.g. EN 166) marked on the product.",
            "de": "PSA: Vor Gebrauch Gebrauchsanweisung lesen. Schutzstufe und Norm (z. B. EN 166) auf dem Produkt angegeben.",
            "fr": "EPI : lire la notice avant utilisation. Niveau de protection et norme (ex. EN 166) indiqués sur le produit.",
            "es": "EPI: leer las instrucciones antes de usar. Nivel de protección y norma (p. ej. EN 166) marcados en el producto.",
            "it": "DPI: leggere le istruzioni prima dell'uso. Livello di protezione e norma (es. EN 166) indicati sul prodotto.",
            "pl": "ŚOI: Przed użyciem przeczytać instrukcję. Poziom ochrony i norma (np. EN 166) podane na produkcie.",
            "ro": "EIP: Citiți instrucțiunile înainte de utilizare. Nivelul de protecție și standardul (ex. EN 166) sunt marcate pe produs.",
        },
    },
    {
        "category": "childcare",
        "label": "母婴用品",
        "keywords": ["baby", "infant", "pacifier", "stroller", "crib", "bottle feeder",
                     "toddler", "nipple", "哺乳", "婴儿", "宝宝"],
        "directives": ["EN 1466 / EN 1888 等婴童用品标准 + GPSR 一般安全要求"],
        "risk": "high",
        "extra": "与食品接触部件须符合 1935/2004/EC；须有看护人陪同警示",
        "warnings": {
            "en": "WARNING: Never leave your child unattended. Always use under the direct supervision of an adult.",
            "de": "ACHTUNG: Kind niemals unbeaufsichtigt lassen. Immer unter Aufsicht eines Erwachsenen verwenden.",
            "fr": "AVERTISSEMENT : Ne jamais laisser l'enfant sans surveillance. Toujours utiliser sous la surveillance d'un adulte.",
            "es": "ADVERTENCIA: Nunca dejar al niño sin vigilancia. Usar siempre bajo la supervisión de un adulto.",
            "it": "AVVERTENZA: Non lasciare mai il bambino incustodito. Usare sempre sotto la supervisione di un adulto.",
            "pl": "OSTRZEŻENIE: Nigdy nie zostawiać dziecka bez nadzoru. Zawsze używać pod nadzorem osoby dorosłej.",
            "ro": "AVERTIZARE: Nu lăsați niciodată copilul nesupravegheat. Utilizați întotdeauna sub supravegherea unui adult.",
        },
    },
    {
        "category": "food_contact",
        "label": "食品接触材料",
        "keywords": ["kitchen", "cookware", "bottle", "mug", "cutlery", "container",
                     "lunch box", "water bottle", "餐", "厨"],
        "directives": ["1935/2004/EC Food Contact Materials"],
        "risk": "medium",
        "extra": "须有酒杯/叉子符号或 'for food use' 标注；标注可耐受温度",
        "warnings": {
            "en": "Food contact safe per 1935/2004/EC. Check max temperature before dishwasher/microwave use.",
            "de": "Lebensmittelecht gemäß 1935/2004/EG. Maximaltemperatur vor Spülmaschine/Mikrowelle prüfen.",
            "fr": "Contact alimentaire conforme au règlement 1935/2004/CE. Vérifier la température max avant lave-vaisselle/micro-ondes.",
            "es": "Apto para contacto alimentario según 1935/2004/CE. Comprobar temperatura máxima antes de lavavajillas/microondas.",
            "it": "A contatto con alimenti secondo il regolamento 1935/2004/CE. Verificare la temperatura massima prima di lavastoviglie/microonde.",
            "pl": "Kontakt z żywnością zgodny z 1935/2004/WE. Sprawdzić maksymalną temperaturę przed użyciem w zmywarce/mikrofalówce.",
            "ro": "Contact alimentar conform 1935/2004/CE. Verificați temperatura maximă înainte de utilizarea mașinii de spălat/cuptorului cu microunde.",
        },
    },
    {
        "category": "cosmetics",
        "label": "化妆品",
        "keywords": ["cosmetic", "serum", "cream", "shampoo", "lotion", "makeup", "化妆品"],
        "directives": ["1223/2009/EC Cosmetics Regulation（需 CPNP 通报 + EU RP 为强制）"],
        "risk": "high",
        "extra": "成分表(INCI)、PIF 档案与 CPNP 通报为强制；欧代不可省略",
        "warnings": {
            "en": "For external use only. Avoid contact with eyes. Discontinue use if irritation occurs. See packaging for full INCI ingredients.",
            "de": "Nur zur äußeren Anwendung. Kontakt mit Augen vermeiden. Bei Reizung Anwendung einstellen. Vollständige INCI-Aufzählung auf der Verpackung.",
            "fr": "Usage externe uniquement. Éviter le contact avec les yeux. Cesser l'utilisation en cas d'irritation. Liste INCI complète sur l'emballage.",
            "es": "Solo para uso externo. Evitar el contacto con los ojos. Suspender el uso si hay irritación. Lista INCI completa en el envase.",
            "it": "Solo per uso esterno. Evitare il contatto con gli occhi. Sospendere l'uso in caso di irritazione. Elenco INCI completo sulla confezione.",
            "pl": "Wyłącznie do użytku zewnętrznego. Unikać kontaktu z oczami. W przypadku podrażnienia zaprzestać użycia. Pełny skład INCI na opakowaniu.",
            "ro": "Doar pentru uz extern. Evitați contactul cu ochii. Întrerupeți utilizarea în caz de iritație. Lista INCI completă pe ambalaj.",
        },
    },
]

# 国家 → 必需警示语语言
COUNTRY_LANGUAGE: Dict[str, str] = {
    "UK": "en", "US": "en", "DE": "de", "FR": "fr", "IT": "it", "ES": "es",
    "PL": "pl", "RO": "ro", "NL": "nl", "SE": "sv", "BG": "bg", "CZ": "cs",
    "HU": "hu", "BE": "fr", "Global": "en", "Nordics": "en",
}

# 语言 → 本地化标题（合规块用）
LANG_HEADER = {
    "en": "Safety & Compliance Information", "de": "Sicherheitshinweise",
    "fr": "Informations de sécurité", "es": "Información de seguridad",
    "it": "Informazioni di sicurezza", "pl": "Informacje dotyczące bezpieczeństwa",
    "ro": "Informații de siguranță", "nl": "Veiligheidsinformatie",
    "sv": "Säkerhetsinformation", "cs": "Bezpečnostní informace",
    "hu": "Biztonsági információ", "bg": "Информация за безопасност",
}


def detect_categories(product_name: str, keywords: List[str]) -> List[Dict]:
    """返回命中的 CE 规则列表（按触发关键词数排序）"""
    text = (product_name + " " + " ".join(keywords)).lower()
    hits = []
    for rule in CE_RULES:
        matched = [kw for kw in rule["keywords"] if kw.lower() in text]
        if matched:
            hits.append({**rule, "matched": matched})
    hits.sort(key=lambda r: -len(r["matched"]))
    return hits


def required_languages(platform: str) -> List[str]:
    """平台覆盖国家 → 去重后的必需警示语语言"""
    from .platform_registry import platform_config
    langs = []
    for country in platform_config(platform)["countries"]:
        lang = COUNTRY_LANGUAGE.get(country, "en")
        if lang not in langs:
            langs.append(lang)
    return langs


def build_checklist(ce_required: bool, categories: List[Dict]) -> List[Dict]:
    """GPSR 法定检查清单（EU 2023/988 Art.9）"""
    items = [
        {"item": "manufacturer_info", "name": "制造商名称+邮政地址+联系方式",
         "required": True,
         "detail": "非欧盟制造商 → 必须展示欧盟境内负责人（欧代）名称+地址+电子联系方式"},
        {"item": "eu_responsible_person", "name": "欧盟授权代表（欧代）",
         "required": True,
         "detail": "中国卖家必须委托欧盟境内经济经营者（欧代服务或自有欧盟实体）"},
        {"item": "product_identification", "name": "产品标识（型号/批次/序列号）",
         "required": True,
         "detail": "产品与包装须有可追溯标识"},
        {"item": "safety_warnings_local", "name": "当地语言安全警示与说明",
         "required": True,
         "detail": "警示语必须用目标市场官方语言，机器翻译质量需人工复核"},
        {"item": "product_images", "name": "商品图片（产品类型+标签/包装）",
         "required": True,
         "detail": "listing 须有清晰产品图，标签类目须额外提供标签/包装图"},
        {"item": "user_manual_local", "name": "当地语言说明书",
         "required": ce_required,
         "detail": "CE 类目强制；非 CE 类目建议提供"},
    ]
    if ce_required:
        items.append({"item": "ce_marking", "name": "CE 标识（清晰、永久、易见）",
                      "required": True,
                      "detail": "贴在产品或包装上，尺寸比例不得变形；DOF（符合性声明）须可应平台要求随时提供"})
    else:
        items.append({"item": "ce_marking", "name": "CE 标识",
                      "required": False,
                      "detail": "当前类目未识别到 CE 指令要求（如属其他 CE 类目请人工确认）"})
    return items


def gpsr_block_text(platform: str, categories: List[Dict],
                    languages: List[str], product_name: str) -> str:
    """生成可粘贴进 listing 的 GPSR 合规块（当地语言警示 + 欧代占位）"""
    lines = []
    for lang in languages[:4]:  # 最多 4 种语言，避免超平台描述限制
        header = LANG_HEADER.get(lang, LANG_HEADER["en"])
        lines.append(f"[{lang.upper()}] {header}")
        lines.append("  Responsible Economic Operator (EU): [欧代公司名称], [欧代地址], [联系邮箱]")
        lines.append(f"  Product: {product_name} | Model/Batch: [型号/批次]")
        for rule in categories:
            w = rule["warnings"].get(lang) or rule["warnings"]["en"] + " (EN)"
            lines.append(f"  • {w}")
        lines.append("")
    lines.append("ℹ️ 使用前请将 [方括号] 内占位符替换为你的欧代真实信息；"
                 "DOF 符合性声明文件须可随时向平台出示。")
    return "\n".join(lines)


def check(product_name: str, keywords: List[str], platform: str) -> Dict:
    """GPSR 合规体检主入口（确定性输出，零 LLM 依赖）"""
    categories = detect_categories(product_name, keywords)
    ce_required = any(r["risk"] == "high" for r in categories)
    directives = list(dict.fromkeys(
        d for r in categories for d in r["directives"]))
    languages = required_languages(platform)

    if categories:
        risk = "high" if ce_required else "medium"
        matched = "、".join(r["label"] for r in categories)
        extra_notes = " ".join(r["extra"] for r in categories)
    else:
        risk = "low"
        matched = "未识别到受监管类目"
        directives = []
        extra_notes = "按 GPSR 一般安全要求执行：仍需欧代+当地语言安全信息（Art.9 基本义务）"

    return {
        "risk_level": risk,
        "platform": platform,
        "ce_required": ce_required,
        "matched_categories": matched,
        "ce_directives": directives,
        "required_languages": languages,
        "category_notes": extra_notes,
        "checklist": build_checklist(ce_required, categories),
        "gpsr_block": gpsr_block_text(platform, categories, languages, product_name),
    }
