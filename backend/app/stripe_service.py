"""Stripe 收款核心逻辑

设计原则：
- 未配置 STRIPE_SECRET_KEY → 本地模拟模式（演示/联调用），路由层负责降级
- webhook 事件处理拆成纯函数，不依赖 stripe SDK，便于单测
- price_id → plan 映射来自 settings（Stripe 后台创建的三个 recurring price）
"""
from datetime import datetime

from sqlalchemy.orm import Session

from .database import User
from .config import settings

# plan → settings 里价格字段名
PRICE_FIELD = {
    "starter": "stripe_price_starter",
    "pro": "stripe_price_pro",
    "business": "stripe_price_business",
}


def map_price_to_plan(price_id: str) -> str | None:
    """Stripe price_id 反查套餐名；未匹配返回 None（未知价格忽略）"""
    if not price_id:
        return None
    for plan, field in PRICE_FIELD.items():
        if getattr(settings, field, "") == price_id:
            return plan
    return None


def apply_checkout_completed(db: Session, user: User, *, plan: str,
                             customer_id: str, subscription_id: str,
                             status: str) -> None:
    """checkout.session.completed：开通套餐"""
    user.plan = plan
    user.stripe_customer_id = customer_id or ""
    user.stripe_subscription_id = subscription_id or ""
    user.stripe_status = status or "active"
    user.updated_at = datetime.utcnow()
    db.commit()


def apply_subscription_deleted(db: Session, user: User) -> None:
    """customer.subscription.deleted：降回免费版"""
    user.plan = "free"
    user.stripe_status = "canceled"
    user.stripe_subscription_id = ""
    user.updated_at = datetime.utcnow()
    db.commit()


def apply_payment_failed(db: Session, user: User) -> None:
    """invoice.payment_failed：标记欠费（保留套餐，由 retry 逻辑决定后续）"""
    user.stripe_status = "past_due"
    user.updated_at = datetime.utcnow()
    db.commit()


def create_checkout_session(user: User, plan: str, origin: str) -> dict:
    """创建 Stripe Checkout Session（subscription 模式）

    返回 {"url": ..., "session_id": ...}；配置缺失时抛 ValueError。
    """
    import stripe  # 懒导入：未安装 stripe 包时仅在真实收款路径报错

    price_field = PRICE_FIELD.get(plan)
    if not price_field:
        raise ValueError(f"plan '{plan}' is not purchasable")
    if not settings.stripe_secret_key:
        raise ValueError("stripe_secret_key not configured")
    price_id = getattr(settings, price_field, "")
    if not price_id:
        raise ValueError(f"stripe price for '{plan}' not configured")

    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user.email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{origin}/app?checkout=success&plan={plan}",
        cancel_url=f"{origin}/pricing?checkout=cancelled",
        client_reference_id=user.id,
        metadata={"user_id": user.id, "plan": plan},
        subscription_data={"metadata": {"user_id": user.id, "plan": plan}},
    )
    return {"url": session.url, "session_id": session.id}
