"""订阅与计费
- 未配置 Stripe Key：本地模拟升降级（联调/演示用）
- 配置 Stripe Key：POST /subscription 返回 Stripe Checkout 支付链接，
  POST /webhook 接收 Stripe 事件自动开通/降级
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db, User
from ..schemas import SubscriptionCreate, SubscriptionInfo
from ..auth import get_current_user
from ..config import settings
from ..billing import (
    PLANS, plan_config, usage_today, usage_this_month,
    upgrade_plan_local, downgrade_to_free,
)
from .. import stripe_service
from .analytics import track_event

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/plans", summary="套餐价目表")
def list_plans():
    return PLANS


@router.get("/subscription", response_model=SubscriptionInfo, summary="当前订阅与用量")
def get_subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = plan_config(user.plan)
    return SubscriptionInfo(
        plan=user.plan,
        stripe_status=user.stripe_status,
        monthly_price_usd=cfg["monthly_price_usd"],
        usage_today=usage_today(db, user.id),
        daily_limit=cfg["daily_limit"],
        monthly_limit=cfg["monthly_calls"],
    )


@router.post("/subscription", summary="升级/变更订阅（返回支付链接或本地模拟开通）")
def create_or_change_subscription(
    body: SubscriptionCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if settings.stripe_secret_key:
        # 生产路径：Stripe Checkout（订阅模式）
        if body.plan == "free":
            return downgrade_to_free(db, user)
        try:
            origin = str(request.base_url).rstrip("/")
            sess = stripe_service.create_checkout_session(user, body.plan, origin)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:  # stripe.APIError 等
            logger.exception("stripe checkout failed")
            raise HTTPException(status_code=502, detail=f"Stripe error: {e}")
        track_event(db, "upgrade", user_id=user.id, platform=None,
                    meta={"plan": body.plan, "mode": "stripe_checkout"})
        return {"success": True, "mode": "stripe",
                "checkout_url": sess["url"], "session_id": sess["session_id"]}

    # 本地模拟模式（未配置 Stripe）
    result = upgrade_plan_local(db, user, body.plan)
    # 验证闭环埋点：付费转化
    track_event(db, "upgrade", user_id=user.id, platform=None,
                meta={"plan": body.plan, "mode": "local"})
    return result


@router.post("/webhook", summary="Stripe webhook（自动开通/降级，配 STRIPE_WEBHOOK_SECRET 后生效）")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if settings.stripe_secret_key:
        import stripe
        try:
            event = stripe.Webhook.construct_event(
                payload, sig, settings.stripe_webhook_secret)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid webhook: {e}")
        data = event["data"]["object"]
    else:
        # 无密钥时的联调模式：直接解析 JSON（生产环境 Stripe 强制验签）
        import json
        try:
            event = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid json")
        data = event.get("data", {}).get("object", {})

    etype = event.get("type", "")
    meta = data.get("metadata") or {}
    uid = data.get("client_reference_id") or meta.get("user_id") or ""
    user = db.query(User).filter(User.id == uid).first() if uid else None
    if user is None and data.get("customer_email"):
        user = db.query(User).filter(
            User.email == data["customer_email"]).first()

    if etype == "checkout.session.completed":
        plan = (meta.get("plan")
                or stripe_service.map_price_to_plan(
                    (data.get("line_items") or {}).get("data", [{}])[0]
                    .get("price", {}).get("id", "")))
        if user and plan:
            stripe_service.apply_checkout_completed(
                db, user, plan=plan,
                customer_id=data.get("customer") or "",
                subscription_id=data.get("subscription") or "",
                status="active")
            track_event(db, "upgrade_paid", user_id=user.id, platform=None,
                        meta={"plan": plan, "mode": "stripe_webhook"})
    elif etype == "customer.subscription.deleted":
        if user:
            stripe_service.apply_subscription_deleted(db, user)
    elif etype == "invoice.payment_failed":
        if user:
            stripe_service.apply_payment_failed(db, user)

    return {"received": True, "type": etype, "user_found": bool(user)}


@router.delete("/subscription", summary="取消订阅（降回免费版）")
def cancel_subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return downgrade_to_free(db, user)
