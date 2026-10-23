"""
计费与用量模块
- 套餐定义（免费 / Starter / Pro / Business）
- 每日免费额度 + 月度额度
- 用量记录走数据库（本地 SQLite 即用）；生产可切 Redis 计数器
- Stripe 集成做成可选依赖：未配置 Key 时 create/upgrade 走"本地模拟"，
  生产配置 Key 后走真实 Stripe Billing
"""
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .database import UsageLog, User

PLANS: dict = {
    "free": {
        "monthly_price_usd": 0,
        "daily_limit": 5,
        "monthly_calls": 150,          # 5 × 30
        "platforms": 1,
        "features": ["product_desc"],
    },
    "starter": {
        "monthly_price_usd": 29,
        "daily_limit": 50,
        "monthly_calls": 1000,
        "platforms": 1,
        "features": ["product_desc"],
    },
    "pro": {
        "monthly_price_usd": 79,
        "daily_limit": 200,
        "monthly_calls": None,         # 无限（仍有日限流保护）
        "platforms": 3,
        "features": ["product_desc", "customer_service", "ad_copy"],
    },
    "business": {
        "monthly_price_usd": 199,
        "daily_limit": 1000,
        "monthly_calls": None,
        "platforms": None,             # 无限
        "features": ["product_desc", "customer_service", "ad_copy", "api_access"],
    },
}


def plan_config(plan: str) -> dict:
    return PLANS.get(plan, PLANS["free"])


def usage_today(db: Session, user_id: str) -> int:
    return (
        db.query(UsageLog)
        .filter(UsageLog.user_id == user_id, UsageLog.log_date == date.today())
        .count()
    )


def usage_this_month(db: Session, user_id: str) -> int:
    today = date.today()
    return (
        db.query(UsageLog)
        .filter(
            UsageLog.user_id == user_id,
            UsageLog.log_date >= today.replace(day=1),
        )
        .count()
    )


def check_and_record_usage(db: Session, user: User, feature: str) -> None:
    """检查额度并记录一次调用；超限抛 402"""
    cfg = plan_config(user.plan)

    if feature not in cfg["features"] and "all" not in cfg["features"]:
        raise HTTPException(
            status_code=402,
            detail=f"当前套餐（{user.plan}）不含「{feature}」功能，请升级套餐",
        )

    used_today = usage_today(db, user.id)
    if used_today >= cfg["daily_limit"]:
        raise HTTPException(
            status_code=402,
            detail=f"今日免费额度已用完（{cfg['daily_limit']} 次/天），明日恢复或升级套餐",
        )

    monthly = cfg["monthly_calls"]
    if monthly is not None and usage_this_month(db, user.id) >= monthly:
        raise HTTPException(
            status_code=402,
            detail=f"本月调用次数已达上限（{monthly} 次），请升级套餐",
        )

    db.add(UsageLog(user_id=user.id, feature=feature))
    db.commit()


def upgrade_plan_local(db: Session, user: User, plan: str) -> dict:
    """本地模拟升级（Stripe 未配置时的降级路径，用于联调/演示）
    生产环境中此函数由 Stripe webhook 回调替代。
    """
    if plan not in ("starter", "pro", "business"):
        raise HTTPException(status_code=400, detail="无效套餐")
    user.plan = plan
    user.stripe_status = "active_local"
    db.commit()
    return {"success": True, "plan": plan, "mode": "local_mock"}


def downgrade_to_free(db: Session, user: User) -> dict:
    user.plan = "free"
    user.stripe_status = "canceled"
    db.commit()
    return {"success": True, "plan": "free"}
