"""
广告文案专家 — Facebook / Google / TikTok 多平台适配

各平台硬性字数限制（超出会校验报给前端）：
- Facebook: 主文案 ≤125（建议），headline ≤40，description ≤30
- Google Ads: 标题 ≤30 ×2，描述 ≤90
- TikTok: 脚本式文案，前 3 秒 hook + CTA + hashtag
"""
import json
from ..llm import LLMClient
from ..schemas import AdCopyRequest, AdCopyResponse

PLATFORM_LIMITS = {
    "facebook": {"primary_text": 125, "headline": 40, "description": 30},
    "google": {"primary_text": 90, "headline": 30, "description": 90},
    "tiktok": {"primary_text": 150, "headline": 50, "description": 60},
}


class AdCopyExpert:
    name = "ad_copy"
    description = "跨境电商广告文案专家"

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def build_prompt(self, req: AdCopyRequest) -> str:
        limits = PLATFORM_LIMITS[req.platform]
        return f"""You are an expert social-media ad copywriter (ad copy).

【产品】{req.product_name}
【平台】{req.platform}
【目标受众】{req.target_audience}
【独特卖点】{req.unique_selling_point}
【语气】{req.tone}

【平台规则】
- primary_text ≤ {limits['primary_text']} chars
- headline ≤ {limits['headline']} chars
- description ≤ {limits['description']} chars
- 1 个明确 CTA；3-5 个 hashtag；抓住 {req.platform} 用户前 3 秒注意力

只输出 JSON：
{{
  "primary_text": "...",
  "headline": "...",
  "description": "...",
  "cta": "Shop Now",
  "hashtags": ["#...", "#..."]
}}"""

    def generate(self, req: AdCopyRequest) -> AdCopyResponse:
        raw = self.llm.chat(
            self.build_prompt(req), temperature=0.8, max_tokens=800, json_mode=True
        )
        data = self.llm.extract_json(raw)
        if not data:
            raise ValueError(f"AI 返回内容无法解析为 JSON: {raw[:200]}")

        primary = str(data.get("primary_text", "")).strip()
        headline = str(data.get("headline", "")).strip()
        desc = str(data.get("description", "")).strip()
        cta = str(data.get("cta", "Shop Now")).strip()
        hashtags = [str(h) for h in data.get("hashtags", []) if str(h).strip()][:5]

        limits = PLATFORM_LIMITS[req.platform]
        # 超限截断（保住平台合规，前端提示用户手动微调）
        primary = primary[: limits["primary_text"]] or primary
        headline = headline[: limits["headline"]] or headline
        desc = desc[: limits["description"]] or desc

        return AdCopyResponse(
            primary_text=primary,
            headline=headline,
            description=desc,
            cta=cta,
            hashtags=hashtags,
            character_counts={
                "primary_text": len(primary),
                "headline": len(headline),
                "description": len(desc),
            },
        )
