"""
产品描述生成专家 — 核心付费功能

能力：
1. 按平台规则（platform_registry.py 注册的 11 个平台）生成合规标题
2. 五点描述（痛点→功能→场景→品质→售后 黄金公式）
3. 详情页描述 + 后台搜索词
4. 语言自动匹配平台主推市场（Allegro→波兰语、Otto→德语、Cdiscount→法语…）
5. 平台合规校验 + 优化评分
"""
from ..llm import LLMClient
from .platform_registry import PLATFORMS, platform_config, rules
from ..schemas import (
    ProductDescriptionRequest,
    ProductDescriptionResponse,
    BulletPoint,
)

LANGUAGE_NAMES = {
    "en": "English", "de": "German", "fr": "French", "es": "Spanish",
    "it": "Italian", "ar": "Arabic", "tr": "Turkish", "hi": "Hindi",
    "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "pl": "Polish", "ro": "Romanian",
}


class ProductDescriptionExpert:
    name = "product_desc"
    description = "跨境电商产品描述生成专家"

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def resolve_language(self, req: ProductDescriptionRequest) -> str:
        """未指定语言时，按平台主推市场自动选择"""
        return req.language or platform_config(req.platform)["language"]

    def build_prompt(self, req: ProductDescriptionRequest, language: str) -> str:
        usp = "、".join(req.unique_selling_points) if req.unique_selling_points else "未指定"
        audience = req.target_audience or "general consumers"
        lang_name = LANGUAGE_NAMES.get(language, language)
        cfg = platform_config(req.platform)
        notes = "\n".join(f"- {n}" for n in cfg["notes"])
        return f"""You are an expert cross-border e-commerce copywriter (product_description).

【产品名称】{req.product_name}
【核心关键词】{', '.join(req.keywords)}
【目标平台】{req.platform}（{cfg['display']}，站点：{', '.join(cfg['countries'])}）
【目标语言】{lang_name}
【语气风格】{req.tone}
【目标受众】{audience}
【独特卖点】{usp}

【平台规则（必须遵守）】
1. 标题不超过 {cfg['title_max']} 字符，前 3 个词必须包含核心关键词
2. 恰好输出 5 条 bullet_points，每条 = {{"heading": "...", "content": "..."}}
3. 五点描述黄金公式：痛点 → 核心功能 → 使用场景 → 材质品质 → 售后保障
4. search_terms 不超过 {cfg['search_terms_max']} 字节，逗号分隔，不重复标题已有关键词
5. 禁止促销词（best/cheapest）、联系方式、主观夸大

【平台特殊要求】
{notes}

【输出要求】
全部内容用 {lang_name} 撰写。只输出 JSON，不要任何解释：
{{
  "title": "...",
  "bullet_points": [{{"heading": "...", "content": "..."}}, ... 5 items],
  "description": "150-400 chars, include use scenarios",
  "search_terms": "...",
  "platform_compliant": true
}}"""

    def generate(self, req: ProductDescriptionRequest) -> ProductDescriptionResponse:
        language = self.resolve_language(req)
        raw = self.llm.chat(
            self.build_prompt(req, language), temperature=0.7, max_tokens=1800,
            json_mode=True,
        )
        data = self.llm.extract_json(raw)
        if not data:
            raise ValueError(f"AI 返回内容无法解析为 JSON: {raw[:200]}")

        title = str(data.get("title", "")).strip()
        bullets_raw = data.get("bullet_points", [])
        bullets = []
        for b in bullets_raw[:5]:
            if isinstance(b, dict) and b.get("content"):
                bullets.append(BulletPoint(
                    heading=str(b.get("heading", "")).strip(),
                    content=str(b.get("content", "")).strip(),
                ))
            elif isinstance(b, str) and b.strip():
                bullets.append(BulletPoint(heading="", content=b.strip()))

        description = str(data.get("description", "")).strip()
        search_terms = str(data.get("search_terms", "")).strip()

        violations, score = self.validate(
            title=title, bullets=bullets, description=description,
            search_terms=search_terms, req=req,
        )

        # GPSR 合规块（CE 类目自动触发）
        gpsr_risk, gpsr_block = None, None
        if req.with_gpsr:
            from .gpsr import check as gpsr_check
            report = gpsr_check(req.product_name, req.keywords, req.platform)
            if report["ce_required"]:
                gpsr_risk = report["risk_level"]
                gpsr_block = report["gpsr_block"]
                # 有合规要求时给质量分加成信号（提交合规块才算完整 listing）
                score = min(score + 3, 100.0)

        # Rufus/iZi 语义搜索适配评分（买家高频问题覆盖度）
        from .semantics import score_semantics
        sem = score_semantics(
            title, [f"{b.heading} {b.content}" for b in bullets], description)
        score = min(score + sem["score"] / 100 * 7, 100.0)  # 语义分最多贡献 7 分

        return ProductDescriptionResponse(
            title=title,
            bullet_points=bullets,
            description=description,
            search_terms=search_terms,
            character_count=len(title),
            platform_compliant=len(violations) == 0,
            optimization_score=round(score, 1),
            violations=violations,
            language=language,
            gpsr_risk_level=gpsr_risk,
            gpsr_block=gpsr_block,
            semantic_score=sem["score"],
            semantic_gaps=sem["gaps"],
        )

    # ---------- 平台合规校验 + 优化评分 ----------
    def validate(self, *, title, bullets, description, search_terms,
                 req: ProductDescriptionRequest):
        r = rules(req.platform)
        violations = []

        if len(title) > r["title_max"]:
            violations.append(
                f"标题 {len(title)} 字符，超过 {req.platform} 上限 {r['title_max']}"
            )
        if len(bullets) != r["bullets"]:
            violations.append(f"需要 {r['bullets']} 条五点描述，实际 {len(bullets)} 条")
        if len(search_terms.encode("utf-8")) > r["search_terms_max"]:
            violations.append("搜索词超出平台字节限制")

        # 优化评分
        score = 50.0
        tl = title.lower()
        kw_hits = sum(1 for kw in req.keywords[:3] if kw.lower() in tl)
        score += min(kw_hits, 3) * 8          # 关键词覆盖 +24
        if 0 < len(description) <= 800:
            score += 10
        elif len(description) > 800:
            score += 5
        if len(bullets) == 5:
            score += 10
            if all(b.heading for b in bullets):
                score += 5
        if not violations:
            score += 5
        return violations, min(score, 100.0)
