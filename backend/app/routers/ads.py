"""广告文案生成与历史"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db, User, AdCopy
from ..schemas import AdCopyRequest, AdCopyResponse
from ..auth import get_current_user
from ..experts.ad_copy import AdCopyExpert
from ..billing import check_and_record_usage

router = APIRouter()
expert = AdCopyExpert()


@router.post("/generate", response_model=AdCopyResponse, summary="生成广告文案")
def generate_ad(
    req: AdCopyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_and_record_usage(db, user, "ad_copy")
    result = expert.generate(req)
    db.add(AdCopy(
        user_id=user.id,
        platform=req.platform,
        product_name=req.product_name,
        primary_text=result.primary_text,
        headline=result.headline,
        ad_description=result.description,
        cta=result.cta,
        hashtags=result.hashtags,
    ))
    db.commit()
    return result


@router.get("/history", summary="文案历史（分页）")
def list_ads(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(AdCopy)
        .filter(AdCopy.user_id == user.id)
        .order_by(AdCopy.created_at.desc())
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": r.id,
                "platform": r.platform,
                "product_name": r.product_name,
                "primary_text": r.primary_text,
                "headline": r.headline,
                "description": r.ad_description,
                "cta": r.cta,
                "hashtags": r.hashtags,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
