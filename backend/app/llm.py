"""
LLM 客户端 — 智谱 GLM-4（OpenAI 兼容接口）
- 配置了 LLM_API_KEY 时走真实 API
- 未配置时自动降级为 MockLLM：返回确定性的结构化结果，
  保证本地开发与验收测试零外部依赖
"""
import json
import logging
import re
from typing import List, Dict, Optional

import httpx

from .config import settings

logger = logging.getLogger("crossbot.llm")


class LLMError(Exception):
    pass


class LLMClient:
    """OpenAI 兼容 chat.completions 客户端"""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model
        self.mock = not bool(self.api_key)
        if self.mock:
            logger.warning("未配置 LLM_API_KEY，运行在 Mock 模式（结果为演示数据）")

    def chat(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1500,
        json_mode: bool = False,
    ) -> str:
        if self.mock:
            return self._mock_response(prompt)

        payload = {
            "model": self.model,
            "messages": ([{"role": "system", "content": system}] if system else [])
            + [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise LLMError(f"LLM 调用失败: {e}") from e

    # ---------- JSON 解析工具 ----------
    @staticmethod
    def extract_json(text: str) -> Optional[dict]:
        """从 LLM 输出中稳健提取 JSON 对象"""
        # 先尝试直接解析
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass
        # 再尝试提取 ```json ... ``` 或第一个 {...}
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                return None
        return None

    # ---------- Mock 实现 ----------
    def _mock_response(self, prompt: str) -> str:
        p = prompt.lower()

        if "product_description" in p or "生成产品描述" in p:
            name = self._extract_field(prompt, "产品名称")
            platform = self._extract_field(prompt, "目标平台") or "amazon"
            kws = self._extract_field(prompt, "核心关键词") or "quality, value"
            kw_list = [k.strip() for k in kws.split(",") if k.strip()][:5]
            title = f"{name} — {' '.join(kw_list[:3])}".strip()[:200]
            bullets = [
                {"heading": "Solves Your Problem", "content": f"{name} is designed around the #1 pain point of real users."},
                {"heading": "Core Features", "content": f"Equipped with {kw_list[0]} technology for reliable daily performance."},
                {"heading": "Use Anywhere", "content": "Perfect for home, office, travel and outdoor scenarios."},
                {"heading": "Built to Last", "content": "Premium materials, strict QC — backed by a 12-month warranty."},
                {"heading": "Risk-Free Purchase", "content": "30-day no-question return policy and friendly 24/7 support."},
            ]
            return json.dumps({
                "title": title,
                "bullet_points": bullets,
                "description": (
                    f"{name} combines {', '.join(kw_list[:2])} in one product. "
                    "Designed for everyday use, tested for durability, and loved by customers. "
                    "Ideal as a gift for family and friends."
                ),
                "search_terms": " ".join(kw_list),
                "character_count": len(title),
                "platform_compliant": True,
                "optimization_score": 82,
                "_mock": True, "_platform": platform,
            }, ensure_ascii=False)

        if "intent" in p and "只输出" in p and "product_info" in p:
            # 意图分类
            for intent, hint in [
                ("tracking", ["where is", "track", "物流", "发货", "快递", "订单"]),
                ("return", ["return", "refund", "退货", "退款"]),
                ("complaint", ["broken", "terrible", "angry", "投诉", "损坏", "不满"]),
                ("product_info", ["size", "material", "spec", "尺寸", "材质", "规格"]),
            ]:
                if any(h in p for h in hint):
                    return intent
            return "other"

        if "情感" in p or "sentiment" in p:
            if any(w in p for w in ["very_negative", "broken", "angry", "scam", "愤怒", "骗子", "损坏"]):
                return "negative"
            return "neutral"

        if "ad" in p and ("facebook" in p or "google" in p or "tiktok" in p or "广告" in p):
            name = self._extract_field(prompt, "产品") or "Our Product"
            audience = self._extract_field(prompt, "受众") or "smart shoppers"
            usp = self._extract_field(prompt, "卖点") or "game-changing quality"
            return json.dumps({
                "primary_text": f"🔥 {name} — {usp}. Loved by {audience}. Try it risk-free today!",
                "headline": f"{name}: {usp[:30]}",
                "description": "Free shipping · 30-day returns · 24/7 support",
                "cta": "Shop Now",
                "hashtags": ["#deals", "#shopping", "#new"],
                "_mock": True,
            }, ensure_ascii=False)

        # 兜底
        return "OK (mock)"

    @staticmethod
    def _extract_field(prompt: str, label: str) -> Optional[str]:
        """兼容两种排版：【label】value 与 label：value"""
        m = re.search(rf"【{label}】\s*(.+)", prompt)
        if not m:
            m = re.search(rf"{label}\s*[:：]\s*(.+)", prompt)
        if m:
            value = m.group(1).split("\n")[0].strip()
            return value or None
        return None


# 模块级单例
llm = LLMClient()
