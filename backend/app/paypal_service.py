"""PayPal 订阅收款核心逻辑（与 Stripe 并行的支付通道）

设计原则：
- 未配置 PAYPAL_CLIENT_ID → 路由层降级为本地模拟/Stripe
- 纯函数（plan 映射、事件处理）与网络调用分离，便于单测
- 用 httpx 调 PayPal REST API（v1/billing/subscriptions），httpx 已是依赖
- 事件 → 套餐开通复用 stripe_service 的 apply_* 函数（同一 User 字段）
"""
import logging

import httpx
from sqlalchemy.orm import Session

from .database import User
from .config import settings
from . import stripe_service

logger = logging.getLogger(__name__)

API = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}

PLAN_FIELD = {
    "starter": "paypal_plan_starter",
    "pro": "paypal_plan_pro",
    "business": "paypal_plan_business",
}

# PayPal 事件 → 动作
EVENT_ACTIVATED = {"BILLING.SUBSCRIPTION.ACTIVATED",
                   "BILLING.SUBSCRIPTION.RENEWED"}
EVENT_CANCELLED = {"BILLING.SUBSCRIPTION.CANCELLED",
                   "BILLING.SUBSCRIPTION.SUSPENDED",
                   "BILLING.SUBSCRIPTION.EXPIRED"}
EVENT_SIGNED = {"PAYMENT.SALE.COMPLETED"}   # 扣款成功（保持套餐）


def map_plan_id_to_plan(plan_id: str) -> str | None:
    if not plan_id:
        return None
    for plan, field in PLAN_FIELD.items():
        if getattr(settings, field, "") == plan_id:
            return plan
    return None


def configured() -> bool:
    return bool(settings.paypal_client_id and settings.paypal_client_secret)


def _base_url() -> str:
    return API.get(settings.paypal_env, API["sandbox"])


async def _access_token(client: httpx.AsyncClient) -> str:
    resp = await client.post(
        f"{_base_url()}/v1/oauth2/token",
        auth=(settings.paypal_client_id, settings.paypal_client_secret),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def create_subscription(user: User, plan: str, origin: str) -> dict:
    """创建 PayPal 订阅，返回 {id, approve_url}；配置缺失/不可购时抛 ValueError"""
    if not configured():
        raise ValueError("paypal credentials not configured")
    field = PLAN_FIELD.get(plan)
    if not field:
        raise ValueError(f"plan '{plan}' is not purchasable")
    plan_id = getattr(settings, field, "")
    if not plan_id:
        raise ValueError(f"paypal plan for '{plan}' not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        token = await _access_token(client)
        resp = await client.post(
            f"{_base_url()}/v1/billing/subscriptions",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={
                "plan_id": plan_id,
                "custom_id": user.id,
                "subscriber": {"email_address": user.email},
                "application_context": {
                    "brand_name": "CrossBot AI",
                    "user_action": "SUBSCRIBE_NOW",
                    "return_url": f"{origin}/app?checkout=success&plan={plan}&via=paypal",
                    "cancel_url": f"{origin}/pricing?checkout=cancelled",
                },
            },
        )
        if resp.status_code >= 400:
            logger.error("paypal create_subscription failed: %s", resp.text)
            raise ValueError(f"PayPal API error {resp.status_code}")
        data = resp.json()
    approve = next((l["href"] for l in data.get("links", [])
                    if l.get("rel") == "approve"), "")
    return {"id": data.get("id", ""), "approve_url": approve}


async def verify_webhook(headers: dict, body: bytes) -> bool:
    """调 PayPal 验签 API；未配置 webhook_id 时返回 False（联调模式由路由层决定）"""
    if not (configured() and settings.paypal_webhook_id):
        return False
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _access_token(client)
        resp = await client.post(
            f"{_base_url()}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={
                "auth_algo": headers.get("paypal-auth-algo", ""),
                "cert_url": headers.get("paypal-cert-url", ""),
                "transmission_id": headers.get("paypal-transmission-id", ""),
                "transmission_sig": headers.get("paypal-transmission-sig", ""),
                "transmission_time": headers.get("paypal-transmission-time", ""),
                "webhook_id": settings.paypal_webhook_id,
                "webhook_event": __import__("json").loads(body),
            },
        )
        resp.raise_for_status()
        return resp.json().get("verification_status") == "SUCCESS"


def apply_event(db: Session, user: User, event_type: str, resource: dict) -> str | None:
    """处理 PayPal 事件，返回动作名；plan 从 custom_id 关联的订阅 metadata 不可得时用 plan_id 映射"""
    plan = map_plan_id_to_plan(
        ((resource.get("plan_id")) or "") if isinstance(resource, dict) else "")
    if event_type in EVENT_ACTIVATED:
        if user:
            stripe_service.apply_checkout_completed(
                db, user, plan=plan or user.plan,
                customer_id=resource.get("subscriber", {}).get("payer_id", ""),
                subscription_id=resource.get("id", ""),
                status="active")
        return "activated"
    if event_type in EVENT_CANCELLED:
        if user:
            stripe_service.apply_subscription_deleted(db, user)
        return "cancelled"
    if event_type in EVENT_SIGNED:
        # 扣款成功：套餐维持不变（续费），仅记录
        return "payment_completed"
    return None
