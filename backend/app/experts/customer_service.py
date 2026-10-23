"""
AI 客服专家 — 7×24 自动处理买家咨询

流程：意图分类 → 情感检测 → 政策安全红线检查 → 按意图路由（物流/退货/投诉/通用）
高风险（very_negative 或投诉+负面）自动建议转人工。
红线层（policy_flags 命中时）：只安抚、不承诺、不承认责任，强制转人工 ——
这是对打 Yuma AI 的差异化：通用 AI 客服乱承诺退款/责任会造成真实资金损失。
"""
import json
import re
from ..llm import LLMClient
from ..schemas import CustomerServiceRequest, CustomerServiceResponse

INTENT_KEYWORDS = {
    "tracking": ["where is my order", "track", "tracking", "shipping",
                 "物流", "发货", "快递", "追踪", "包裹", "订单"],
    "return": ["return", "refund", "exchange", "退货", "退款", "换货"],
    "complaint": ["complaint", "broken", "damaged", "scam", "never again",
                  "投诉", "损坏", "质量差", "不满", "骗子"],
    "product_info": ["size", "material", "spec", "compatib", "how to use",
                     "尺寸", "材质", "规格", "兼容", "怎么用"],
}

SENTIMENT_NEGATIVE_WORDS = [
    "angry", "terrible", "worst", "scam", "fraud", "disgusted", "furious",
    "愤怒", "气人", "骗子", "垃圾", "退货", "投诉",
]

# ---------- 政策安全红线层 ----------
# 命中任意一条 → AI 回复切换为「只安抚不承诺」模板 + 强制转人工 + 留证提示
REDLINE_PATTERNS = [
    ("negative_review_threat", [
        r"(remove|delete).{0,20}(review|feedback)", r"(1|one)[- ]star",
        r"unless you (refund|give)", r"or i('| wi)?ll (leave|post|write).{0,20}review",
        r"差评", r"(不|否).{0,6}退款.{0,10}(差评|投诉)",
    ]),
    ("refund_extortion", [
        r"chargeback", r"dispute.{0,10}(the )?(charge|payment|transaction)",
        r"report you to", r"(paypal|bank|credit card).{0,20}(claim|complaint)",
        r"全额退款.{0,15}(否则|不然)", r"(拒付|退一赔)", r"报警",
    ]),
    ("harm_claim", [
        r"injur(y|ed)", r"hurt", r"hospital", r"burn", r"caught (fire|on fire)",
        r"受伤", r"烫伤", r"起火", r"着火", r"进了医院",
    ]),
    ("legal_action", [
        r"lawyer", r"attorney", r"sue you", r"lawsuit", r"court",
        r"律师", r"起诉", r"法院", r"告你",
    ]),
    ("counterfeit_accusation", [
        r"counterfeit", r"fake product", r"not (the )?(original|genuine|authentic)",
        r"假货", r"仿品", r"不是正品",
    ]),
]

REDLINE_REPLY = (
    "We're truly sorry for this experience, and we take it seriously. "
    "Your case has been flagged to our senior support team for priority review — "
    "they will contact you within 24 hours with a resolution. "
    "For everyone's protection we can't discuss refunds or liability here, "
    "but nothing is being ignored. / "
    "非常抱歉给您带来不好的体验，我们已将您的情况标记给资深客服专员优先处理，"
    "将在 24 小时内与您联系并给出解决方案。为了保护双方权益，"
    "线上无法直接确认退款与责任认定，但您的问题绝不会被搁置。"
)

REDLINE_GUARDRAIL = (
    "🚨 红线模式已激活：AI 仅发送安抚话术，未做任何退款/赔偿/责任承诺，"
    "已强制转人工并建议截图留证。切勿让普通客服话术在此类消息上越权。"
)


class CustomerServiceExpert:
    name = "customer_service"
    description = "跨境电商AI客服专家"

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    # ---------- 意图 ----------
    def classify_intent(self, message: str) -> str:
        low = message.lower()
        for intent, kws in INTENT_KEYWORDS.items():
            if any(k in low for k in kws):
                return intent
        # 关键词未命中 → LLM 兜底分类
        prompt = (
            f'分类以下买家消息的意图："{message}"\n'
            "可选意图：tracking, return, complaint, product_info, other\n"
            "只输出意图名称，不要解释。"
        )
        out = self.llm.chat(prompt, temperature=0.1, max_tokens=10).strip().lower()
        return out if out in ("tracking", "return", "complaint", "product_info", "other") else "other"

    # ---------- 情感 ----------
    def detect_sentiment(self, message: str) -> str:
        low = message.lower()
        neg_hits = sum(1 for w in SENTIMENT_NEGATIVE_WORDS if w in low)
        if neg_hits >= 2 or "very negative" in low:
            return "very_negative"
        if neg_hits == 1:
            return "negative"
        if any(w in low for w in ["thank", "great", "love", "perfect", "谢谢", "很好", "喜欢"]):
            return "positive"
        return "neutral"

    # ---------- 政策安全红线 ----------
    def check_redlines(self, message: str) -> list[str]:
        """返回命中的红线类型列表（空 = 未命中）。"""
        low = message.lower()
        flags = []
        for flag, patterns in REDLINE_PATTERNS:
            if any(re.search(p, low) for p in patterns):
                flags.append(flag)
        return flags

    # ---------- 主入口 ----------
    def handle(self, req: CustomerServiceRequest) -> CustomerServiceResponse:
        intent = self.classify_intent(req.customer_message)
        sentiment = self.detect_sentiment(req.customer_message)

        # 红线层优先：命中 → 固定安抚话术 + 强制转人工，不走普通生成
        redline_flags = self.check_redlines(req.customer_message)
        if redline_flags:
            return CustomerServiceResponse(
                reply=REDLINE_REPLY,
                intent=intent,
                sentiment="very_negative" if sentiment != "very_negative" else sentiment,
                confidence=0.95,
                needs_escalation=True,
                escalation_reason=(
                    f"命中政策安全红线（{'、'.join(redline_flags)}）："
                    "需要人工审核后处理，AI 已被限制只安抚不承诺"
                ),
                policy_flags=redline_flags,
                guardrail=REDLINE_GUARDRAIL,
            )

        if intent == "tracking":
            reply = self._tracking_reply(req)
        elif intent == "return":
            reply = self._return_reply()
        elif intent == "product_info":
            reply = self._product_info_reply(req)
        else:
            reply = self._general_reply(req)

        needs_escalation = sentiment == "very_negative" or (
            intent == "complaint" and sentiment in ("negative", "very_negative")
        )
        confidence = 0.9 if intent != "other" else 0.6

        return CustomerServiceResponse(
            reply=reply,
            intent=intent,
            sentiment=sentiment,
            confidence=confidence,
            needs_escalation=needs_escalation,
            escalation_reason="买家情绪负面，建议人工介入跟进" if needs_escalation else None,
            policy_flags=[],
            guardrail=None,
        )

    # ---------- 各意图回复 ----------
    def _tracking_reply(self, req: CustomerServiceRequest) -> str:
        order_id = req.order_id or self._extract_order_id(req.customer_message)
        if not order_id:
            return ("Sure! Could you share your order number (e.g. #123-4567890)? "
                    "I'll check the delivery status for you right away. / "
                    "请提供订单号，我马上帮您查询物流状态。")
        # TODO 生产环境：接入 17track / AfterShip API 查询实时轨迹
        return (f"Thanks! I found order {order_id}. It has been shipped and is on the way. "
                f"Estimated delivery: 3-7 business days. You can track it any time — "
                f"anything else I can help with? / 订单 {order_id} 已发货，"
                f"预计 3-7 个工作日送达，可随时找我查询进度。")

    def _return_reply(self) -> str:
        return ("We're sorry it didn't work out. You're covered by our 30-day no-questions-asked "
                "return policy. Please reply with: 1) your order number, 2) the reason, "
                "3) a photo if the item is damaged — we'll process it within 24 hours. / "
                "支持 30 天无理由退货：请提供订单号、退货原因（如有质量问题附照片），"
                "我们会在 24 小时内处理。")

    def _product_info_reply(self, req: CustomerServiceRequest) -> str:
        prompt = (
            "You are a professional cross-border e-commerce customer service agent (customer_service). "
            "Answer the buyer's product question concisely (under 150 words), friendly and factual. "
            "If unsure, politely offer to escalate to a human agent.\n\n"
            f"Buyer: {req.customer_message}"
        )
        return self.llm.chat(prompt, temperature=0.3, max_tokens=400).strip()

    def _general_reply(self, req: CustomerServiceRequest) -> str:
        prompt = (
            "You are a professional cross-border e-commerce customer service agent (customer_service). "
            "Reply helpfully in under 150 words. Be professional and warm. "
            "If the question needs account or payment access, offer to escalate.\n\n"
            f"Buyer: {req.customer_message}"
        )
        return self.llm.chat(prompt, temperature=0.4, max_tokens=400).strip()

    @staticmethod
    def _extract_order_id(message: str) -> str | None:
        m = re.search(r"#?\b(\d{3}-\d{7}-\d{7}|\d{8,16})\b", message)
        return m.group(1) if m else None
