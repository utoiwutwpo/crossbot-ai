"""
Listing 仓库 + 风险日报路由（Phase 1）
- POST   /listings            添加 listing（立即体检一次）
- POST   /listings/import     批量导入（数组）
- GET    /listings            我的监控列表
- GET    /listings/{id}       详情（风险项 + 修复建议 + GPSR 合规块）
- DELETE /listings/{id}
- POST   /listings/{id}/recheck
- POST   /watch/run           立即跑一轮体检并生成当天日报（等价于每日定时任务）
- GET    /watch/report/latest 最新日报
- GET    /watch/reports       日报历史
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db, ListingWatch, RiskReport, User, gen_id
from ..experts.platform_registry import PLATFORMS
from ..schemas import PlatformType as PlatformIn
from ..watch_service import (WATCH_LIMITS, check_one, report_to_dict,
                             run_user_watch, send_report_email)

router = APIRouter()


class WatchCreateRequest(BaseModel):
    sku: str = ""
    product_name: str = Field(min_length=1, max_length=255)
    platform: PlatformIn
    keywords: List[str] = []
    title: str = ""
    bullets: List[str] = []
    description: str = ""


def _watch_out(w: ListingWatch, detail: bool = False) -> dict:
    d = {
        "id": w.id, "sku": w.sku, "product_name": w.product_name,
        "platform": w.platform, "risk_level": w.risk_level,
        "risk_score": w.risk_score, "risk_count": len(w.risk_items or []),
        "last_checked_at": str(w.last_checked_at or ""),
    }
    if detail:
        d.update({
            "keywords": w.keywords or [], "title": w.title,
            "bullets": w.bullets or [], "description": w.description,
            "risk_items": w.risk_items or [], "fix_hints": w.fix_hints or [],
            "gpsr_block": w.gpsr_block, "prev_risk_level": w.prev_risk_level,
        })
    return d


@router.post("/listings")
def add_listing(body: WatchCreateRequest, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    if body.platform not in PLATFORMS:
        raise HTTPException(400, f"不支持的平台：{body.platform}")
    count = db.query(ListingWatch).filter(ListingWatch.user_id == user.id).count()
    limit = WATCH_LIMITS.get(user.plan, 5)
    if count >= limit:
        raise HTTPException(402, f"当前 {user.plan} 套餐最多监控 {limit} 条 listing，"
                                 "升级套餐可提升上限")
    w = ListingWatch(id=gen_id(), user_id=user.id, sku=body.sku[:100],
                     product_name=body.product_name, platform=body.platform,
                     keywords=body.keywords, title=body.title,
                     bullets=body.bullets, description=body.description)
    db.add(w)
    db.commit()
    diff = check_one(db, w)
    return {"listing": _watch_out(w, detail=True), "first_check": diff}


@router.post("/listings/import")
def import_listings(items: List[WatchCreateRequest],
                    user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    added, errors = [], []
    for i, body in enumerate(items):
        try:
            r = add_listing(body, user, db)
            added.append(r["listing"])
        except HTTPException as exc:
            errors.append({"index": i, "reason": exc.detail})
    return {"added": len(added), "listings": added, "errors": errors}


@router.get("/listings")
def my_listings(user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    rows = (db.query(ListingWatch).filter(ListingWatch.user_id == user.id)
            .order_by(ListingWatch.risk_score).all())
    return {"listings": [_watch_out(w) for w in rows],
            "limit": WATCH_LIMITS.get(user.plan, 5)}


@router.get("/listings/{wid}")
def listing_detail(wid: str, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    w = db.get(ListingWatch, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "listing 不存在")
    return _watch_out(w, detail=True)


class WatchUpdateRequest(BaseModel):
    sku: Optional[str] = None
    product_name: Optional[str] = Field(default=None, max_length=255)
    keywords: Optional[List[str]] = None
    title: Optional[str] = None
    bullets: Optional[List[str]] = None
    description: Optional[str] = None


@router.put("/listings/{wid}")
def update_listing(wid: str, body: WatchUpdateRequest,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """用户修复 listing 后回贴新文案：更新快照并立即重检（恶化会在日报中提示）"""
    w = db.get(ListingWatch, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "listing 不存在")
    for field in ("sku", "product_name", "keywords", "title", "bullets", "description"):
        val = getattr(body, field)
        if val is not None:
            if field == "sku":
                val = val[:100]
            setattr(w, field, val)
    db.commit()
    diff = check_one(db, w)
    return {"listing": _watch_out(w, detail=True), "check": diff}


@router.delete("/listings/{wid}")
def delete_listing(wid: str, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    w = db.get(ListingWatch, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "listing 不存在")
    db.delete(w)
    db.commit()
    return {"deleted": wid}


@router.post("/listings/{wid}/recheck")
def recheck(wid: str, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    w = db.get(ListingWatch, wid)
    if not w or w.user_id != user.id:
        raise HTTPException(404, "listing 不存在")
    diff = check_one(db, w)
    return {"listing": _watch_out(w, detail=True), "check": diff}


@router.post("/watch/run")
def run_watch(user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """立即跑一轮体检 + 生成当天日报（与每日定时任务同一逻辑）"""
    report = run_user_watch(db, user)
    report["email_sent"] = send_report_email(user, report)
    return report


@router.get("/watch/report/latest")
def latest_report(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    r = (db.query(RiskReport).filter(RiskReport.user_id == user.id)
         .order_by(RiskReport.report_date.desc()).first())
    return {"report": report_to_dict(r) if r else None}


@router.get("/watch/reports")
def report_history(user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    rows = (db.query(RiskReport).filter(RiskReport.user_id == user.id)
            .order_by(RiskReport.report_date.desc()).limit(30).all())
    return {"reports": [report_to_dict(r) for r in rows]}
