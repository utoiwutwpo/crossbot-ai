"""
7x24 监控调度器（APScheduler）
每日 watch_daily_hour 点（UTC）对所有用户跑体检轮 + 生成风险日报 + 发邮件。
Railway 单实例部署时随 FastAPI lifespan 启动；多实例/外部 cron 时设
WATCH_SCHEDULER_ENABLED=false 关闭。
"""
import logging

from .database import ListingWatch, SessionLocal, User
from .watch_service import run_user_watch, send_report_email

log = logging.getLogger("crossbot.scheduler")
_scheduler = None


def daily_watch_job() -> dict:
    """每日体检轮：遍历所有有 listing 的用户。返回执行摘要。"""
    db = SessionLocal()
    ran, failed = 0, 0
    try:
        user_ids = [row[0] for row in db.query(User.id).distinct().all()]
        for uid in user_ids:
            user = db.get(User, uid)
            has_listings = db.query(ListingWatch).filter_by(user_id=uid).count() > 0
            if not has_listings:
                continue
            try:
                report = run_user_watch(db, user)
                sent = send_report_email(user, report)
                log.info("日报完成 user=%s total=%s high=%s email=%s",
                         uid, report["total_listings"],
                         report["high_count"], sent)
                ran += 1
            except Exception:
                log.exception("用户 %s 体检轮失败", uid)
                failed += 1
    finally:
        db.close()
    return {"users_processed": ran, "failed": failed}


def start_scheduler() -> None:
    global _scheduler
    from .config import settings
    if not settings.watch_scheduler_enabled:
        log.info("监控调度器已通过配置关闭")
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        daily_watch_job, "cron", hour=settings.watch_daily_hour,
        minute=0, id="daily_watch", replace_existing=True)
    _scheduler.start()
    log.info("监控调度器已启动：每日 %02d:00 UTC 体检 + 风险日报",
             settings.watch_daily_hour)


def stop_scheduler() -> None:
    if _scheduler:
        _scheduler.shutdown(wait=False)
