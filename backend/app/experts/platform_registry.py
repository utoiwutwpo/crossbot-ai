"""
跨境电商平台注册表 — 欧洲主打平台矩阵
覆盖：Amazon 欧洲站 / eBay / Cdiscount / Otto / Allegro / eMAG / Fruugo / Walmart / TikTok Shop

字段说明：
- title_max / bullets / search_terms_max / description_max：listing 硬性限制
  ⚠️ 数值为工程默认值，平台规则会不定期调整，上架前以各平台卖家中心最新文档为准
- language：该平台主推的 listing 默认语言（矩阵生成时未指定语言则用它）
- countries：主要覆盖站点/国家
- notes：生成 prompt 中的平台特殊要求
"""

PLATFORMS: dict = {
    # ===== 全球/泛欧 =====
    "amazon": {
        "display": "Amazon 欧洲站",
        "countries": ["UK", "DE", "FR", "IT", "ES", "NL", "SE", "PL", "BE"],
        "language": "en",
        "title_max": 200, "bullets": 5, "search_terms_max": 249,
        "description_max": 2000,
        "notes": [
            "标题前 3 个词包含核心关键词；德国站标题须为德语",
            "五点描述：痛点→功能→场景→品质→售后",
            "后台搜索词（generic keywords）不重复标题已有关键词，禁用竞品品牌名",
        ],
    },
    "ebay": {
        "display": "eBay",
        "countries": ["UK", "DE", "FR", "IT", "ES"],
        "language": "en",
        "title_max": 80, "bullets": 5, "search_terms_max": 500,
        "description_max": 4000,
        "notes": [
            "标题 80 字符是硬限制，关键词前置",
            "描述支持 HTML；必填 Item Specifics（品牌/型号/兼容性）在结构化字段中单独填写",
        ],
    },
    "fruugo": {
        "display": "Fruugo（泛欧）",
        "countries": ["UK", "DE", "FR", "IT", "ES", "NL", "PL", "Nordics"],
        "language": "en",
        "title_max": 100, "bullets": 5, "search_terms_max": 300,
        "description_max": 3000,
        "notes": [
            "主目录用英语提交，Fruugo 平台自动翻译成各国语言",
            "属性（颜色/尺码/材质）必须结构化填写，否则无法翻译分发",
        ],
    },
    "walmart": {
        "display": "Walmart",
        "countries": ["US"],
        "language": "en",
        "title_max": 100, "bullets": 5, "search_terms_max": 500,
        "description_max": 4000,
        "notes": [
            "标题格式：品牌 + 型号 + 商品名 + 关键属性，禁促销词与特殊字符",
            "Key Features 恰好 3-10 条（工程上统一生成 5 条）",
        ],
    },
    # ===== 法国 =====
    "cdiscount": {
        "display": "Cdiscount",
        "countries": ["FR"],
        "language": "fr",
        "title_max": 120, "bullets": 5, "search_terms_max": 300,
        "description_max": 3000,
        "notes": [
            "全法语 listing，禁英语混杂",
            "描述需包含技术参数表；法国消费者重视保修与退换条款",
        ],
    },
    # ===== 德国 =====
    "otto": {
        "display": "Otto",
        "countries": ["DE"],
        "language": "de",
        "title_max": 70, "bullets": 5, "search_terms_max": 250,
        "description_max": 2500,
        "notes": [
            "纯德语 listing，语法拼写要求高（德国用户敏感）",
            "Otto 对品质描述与材质说明要求严格，避免绝对化宣传用语",
        ],
    },
    # ===== 波兰 =====
    "allegro": {
        "display": "Allegro",
        "countries": ["PL", "CZ", "HU"],
        "language": "pl",
        "title_max": 75, "bullets": 5, "search_terms_max": 300,
        "description_max": 8000,
        "notes": [
            "波兰语 listing；标题 75 字符硬限制",
            "描述支持 HTML；波兰买家重视配送时效与 Allegro Smart 兼容性",
        ],
    },
    # ===== 罗马尼亚/东南欧 =====
    "emag": {
        "display": "eMAG",
        "countries": ["RO", "HU", "BG"],
        "language": "ro",
        "title_max": 150, "bullets": 5, "search_terms_max": 300,
        "description_max": 4000,
        "notes": [
            "罗马尼亚语 listing",
            "必填品类特定结构化字段（家族/品牌/型号），否则审核被拒",
        ],
    },
    # ===== 德国/中东欧 =====
    "kaufland": {
        "display": "Kaufland Global",
        "countries": ["DE", "AT", "CZ", "SK"],
        "language": "de",
        "title_max": 150, "bullets": 5, "search_terms_max": 250,
        "description_max": 4000,
        "notes": [
            "德语 listing（德区为主），拼写语法要求与 Otto 同级",
            "制造商信息必须与 GPSR 欧代/制造商一致",
            "EAN 是商品主键，缺失无法创建",
        ],
    },
    # ===== 荷兰/比利时 =====
    "bol": {
        "display": "bol.com",
        "countries": ["NL", "BE"],
        "language": "nl",
        "title_max": 120, "bullets": 5, "search_terms_max": 200,
        "description_max": 3000,
        "notes": [
            "荷兰语 listing（NL/BE），EAN 是商品唯一键，缺失直接建不了 offer",
            "荷兰买家重视 Delivery Promise 与 bol 分销服务评分",
        ],
    },
    # ===== 自建站/其他（保留原有）=====
    "shopify": {
        "display": "Shopify",
        "countries": ["Global"],
        "language": "en",
        "title_max": 255, "bullets": 5, "search_terms_max": 500,
        "description_max": 10000,
        "notes": ["自建站无硬性平台审核，重点是品牌语气一致性"],
    },
    # ===== TikTok Shop（合规增长主打：内容电商 + 合规内嵌） =====
    "tiktok": {
        "display": "TikTok Shop",
        "countries": ["UK", "US", "ES", "IT", "DE", "FR"],
        "language": "en",
        "title_max": 255, "bullets": 5, "search_terms_max": 200,
        "description_max": 3000,
        "notes": [
            "标题可带 emoji，前 20 字符抓眼球（信息流场景）；描述侧重短视频种草场景与使用瞬间",
            "欧盟站点（ES/IT/DE/FR）同样强制 GPSR/CE 合规：缺欧代与当地语言警示语会被下架",
            "合规红线：禁医妆类夸大功效词（治疗/治愈/瘦身特效）、禁绝对化用语、认证类目须上传资质",
            "搜索词字段用于商品关键词/话题标签（#hashtag），不重复标题",
        ],
    },
}


def platform_config(platform: str) -> dict:
    cfg = PLATFORMS.get(platform)
    if cfg is None:
        raise KeyError(f"未知平台: {platform}")
    return cfg


def rules(platform: str) -> dict:
    """兼容旧调用：返回 title_max/bullets/search_terms_max 三元组"""
    cfg = platform_config(platform)
    return {
        "title_max": cfg["title_max"],
        "bullets": cfg["bullets"],
        "search_terms_max": cfg["search_terms_max"],
    }
