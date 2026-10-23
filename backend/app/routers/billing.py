"""订阅与计费
- 未配置 Stripe Key：本地模拟升降级（联调/演示用）
- 配置 Stripe Key：走真实 Stripe Billing（TODO 上线周实现完整 webhook）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db, User
from ..schemas import SubscriptionCreate, SubscriptionInfo
from ..auth import get_current_user
from ..config import settings
from ..billing import (
    PLANS, plan_config, usage_today, usage_this_month,
    upgrade_plan_local, downgrade_to_free,
)
from .analytics import track_event

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


@router.post("/subscription", summary="升级/变更订阅")
def create_or_change_subscription(
    body: SubscriptionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if settings.stripe_secret_key:
        # 生产路径：创建 Stripe Checkout Session / Subscription
        # TODO(上线周): stripe.Subscription.create + webhook 回写
        return {"success": False, "message": "Stripe 生产集成将在上线周启用，当前为本地模式"}
    result = upgrade_plan_local(db, user, body.plan)
    # 验证闭环埋点：付费转化
    track_event(db, "upgrade", user_id=user.id, platform=None,
                meta={"plan": body.plan})
    return result


@router.delete("/subscription", summary="取消订阅（降回免费版）")
def cancel_subscription(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return downgrade_to_free(db, user)
