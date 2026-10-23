"""产品描述生成与历史（含欧洲多平台市场矩阵）"""
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db, User, ProductDescription
from ..schemas import (
    ProductDescriptionRequest, ProductDescriptionResponse, BulletPoint,
    MarketMatrixRequest, MarketMatrixResponse,
    GpsrCheckRequest, GpsrCheckResponse,
    AttributeValidateRequest, AttributeValidateResponse,
    ReviewInsightRequest, ReviewInsightResponse,
)
from ..auth import get_current_user
from ..experts.product_description import ProductDescriptionExpert
from ..experts.platform_registry import PLATFORMS, platform_config
from ..experts.gpsr import check as gpsr_check
from ..experts.attributes import required_attributes, validate_attributes, detect_category
from ..experts.review_loop import ReviewLoopExpert
from ..routers.analytics import track_event
from ..billing import check_and_record_usage

router = APIRouter()
expert = ProductDescriptionExpert()
review_expert = ReviewLoopExpert()

# ---- 游客体检限频（内存版，MVP 够用；多实例部署时换 Redis） ----
_GUEST_LIMIT = 3               # 每 IP 每天 3 次
_GUEST_HITS: dict = defaultdict(list)
_DAY = 86400


def _guest_rate_ok(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _GUEST_HITS[ip] if now - t < _DAY]
    if len(hits) >= _GUEST_LIMIT:
        _GUEST_HITS[ip] = hits
        return False
    hits.append(now)
    _GUEST_HITS[ip] = hits
    return True


@router.get("/platforms", summary="支持的平台注册表（规则+默认语言）")
def list_platforms():
    return {
        key: {
            "display": cfg["display"],
            "countries": cfg["countries"],
            "language": cfg["language"],
            "title_max": cfg["title_max"],
            "bullets": cfg["bullets"],
            "search_terms_max": cfg["search_terms_max"],
            "description_max": cfg["description_max"],
            "notes": cfg["notes"],
        }
        for key, cfg in PLATFORMS.items()
    }


@router.post("/gpsr/check", response_model=GpsrCheckResponse,
             summary="GPSR 合规体检（免费）：风险等级 + 法定检查清单")
def gpsr_compliance_check(
    req: GpsrCheckRequest,
    user: User = Depends(get_current_user),
):
    """免费只报问题不给答案（合规块付费解锁）——获客钩子。不消耗生成额度。"""
    report = gpsr_check(req.product_name, req.keywords, req.platform)
    is_free = user.plan == "free"
    return GpsrCheckResponse(
        risk_level=report["risk_level"],
        platform=report["platform"],
        ce_required=report["ce_required"],
        matched_categories=report["matched_categories"],
        ce_directives=report["ce_directives"],
        required_languages=report["required_languages"],
        category_notes=report["category_notes"],
        checklist=report["checklist"],
        gpsr_block=None if is_free else report["gpsr_block"],
        asin=req.asin,
        data_source="title_keywords",
        upsell_note=("⚠️ 检测到该产品需 GPSR 合规块（含当地语言警示语）。"
                     "升级 Starter 及以上套餐解锁可粘贴的完整合规块，"
                     "缺合规块可能导致平台下架（EU 2023/988 已强制执行）。"
                     ) if (is_free and report["ce_required"]) else None,
    )


@router.post("/gpsr/check-guest", response_model=GpsrCheckResponse,
             summary="GPSR 合规体检（游客版，免注册）：每 IP 每天 3 次")
def gpsr_check_guest(req: GpsrCheckRequest, request: Request,
                     db: Session = Depends(get_db)):
    """落地页零门槛体验：不注册、不登录、不消耗额度，只报问题不给合规块。"""
    ip = request.client.host if request.client else "unknown"
    if not _guest_rate_ok(ip):
        raise HTTPException(
            status_code=429,
            detail="今日免费体检次数已用完（3 次/天）。注册免费账号可继续体检并保存历史。",
        )
    report = gpsr_check(req.product_name, req.keywords, req.platform)
    # 验证闭环埋点（失败不影响业务；报告算完再记，带上风险等级）
    track_event(db, "guest_check", request, platform=req.platform,
                meta={"risk": report["risk_level"]})
    return GpsrCheckResponse(
        risk_level=report["risk_level"],
        platform=report["platform"],
        ce_required=report["ce_required"],
        matched_categories=report["matched_categories"],
        ce_directives=report["ce_directives"],
        required_languages=report["required_languages"],
        category_notes=report["category_notes"],
        checklist=report["checklist"],
        gpsr_block=None,   # 游客版固定脱敏，合规块是注册/付费后的价值
        asin=req.asin,
        data_source="title_keywords",
        upsell_note=("⚠️ 检测到该产品需 GPSR 合规块（含当地语言警示语）。"
                     "注册免费账号保存体检历史，升级 Starter 解锁可粘贴的完整合规块。"
                     ) if report["ce_required"] else None,
    )


@router.post("/descriptions/generate", response_model=ProductDescriptionResponse,
             summary="生成产品描述（多平台/多语言）")
def generate_description(
    req: ProductDescriptionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_and_record_usage(db, user, "product_desc")
    track_event(db, "generate", user_id=user.id, platform=req.platform)
    try:
        result = expert.generate(req)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    result.platform = req.platform
    record = ProductDescription(
        user_id=user.id,
        product_name=req.product_name,
        platform=req.platform,
        language=req.language,
        tone=req.tone,
        title=result.title,
        bullet_points=[b.model_dump() for b in result.bullet_points],
        description=result.description,
        search_terms=result.search_terms,
        optimization_score=result.optimization_score,
        platform_compliant=result.platform_compliant,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    result.id = record.id
    return result


@router.post("/descriptions/market-matrix", response_model=MarketMatrixResponse,
             summary="欧洲多平台矩阵：一次产品 → 多平台多语言批量生成")
def generate_market_matrix(
    req: MarketMatrixRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """每个平台各计 1 次用量；单平台失败不影响其余平台。"""
    # 去重保序
    platforms = list(dict.fromkeys(req.platforms))
    results: list = []
    errors: list = []

    for i, platform in enumerate(platforms):
        # 用量先检查再生成，避免浪费 AI 调用
        try:
            check_and_record_usage(db, user, "product_desc")
        except HTTPException as e:
            errors.append({
                "platform": platform,
                "error": f"额度不足，剩余 {len(platforms) - i} 个平台未生成：{e.detail}",
            })
            break

        single = ProductDescriptionRequest(
            product_name=req.product_name,
            keywords=req.keywords,
            platform=platform,
            language=req.language,      # None → 平台默认语言
            tone=req.tone,
            target_audience=req.target_audience,
            unique_selling_points=req.unique_selling_points,
        )
        try:
            item = expert.generate(single)
            item.platform = platform
            record = ProductDescription(
                user_id=user.id,
                product_name=req.product_name,
                platform=platform,
                language=item.language,
                tone=req.tone,
                title=item.title,
                bullet_points=[b.model_dump() for b in item.bullet_points],
                description=item.description,
                search_terms=item.search_terms,
                optimization_score=item.optimization_score,
                platform_compliant=item.platform_compliant,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            item.id = record.id
            results.append(item)
        except (ValueError, KeyError) as e:
            db.rollback()
            errors.append({"platform": platform, "error": str(e)[:300]})

    return MarketMatrixResponse(
        product_name=req.product_name,
        requested=len(platforms),
        succeeded=len(results),
        results=results,
        errors=errors,
    )


@router.get("/descriptions", summary="生成历史（分页）")
def list_descriptions(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(ProductDescription)
        .filter(ProductDescription.user_id == user.id)
        .order_by(ProductDescription.created_at.desc())
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": r.id,
                "product_name": r.product_name,
                "platform": r.platform,
                "language": r.language,
                "title": r.title,
                "bullet_points": r.bullet_points,
                "description": r.description,
                "search_terms": r.search_terms,
                "optimization_score": r.optimization_score,
                "platform_compliant": r.platform_compliant,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.get("/descriptions/{desc_id}", summary="单条详情")
def get_description(
    desc_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.get(ProductDescription, desc_id)
    if not r or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {
        "id": r.id,
        "title": r.title,
        "bullet_points": r.bullet_points,
        "description": r.description,
        "search_terms": r.search_terms,
        "optimization_score": r.optimization_score,
        "platform_compliant": r.platform_compliant,
    }


# ---------- 平台属性树（对齐 Marqetir「首过率」卖点） ----------

@router.get("/attributes/{platform}", summary="平台属性树：必填/推荐结构化参数")
def get_attribute_tree(platform: str, category: str = "generic"):
    try:
        platform_config(platform)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知平台: {platform}")
    return {
        "platform": platform,
        "category": category,
        "attributes": required_attributes(platform, category),
        "disclaimer": "属性要求为工程默认值，以卖家中心最新类目模板为准",
    }


@router.post("/attributes/validate", response_model=AttributeValidateResponse,
             summary="校验已填属性：缺失/格式错误/硬阻断 + 完整度")
def validate_platform_attributes(req: AttributeValidateRequest):
    category = (req.category or "generic").strip() or "generic"
    return validate_attributes(req.platform, req.attributes, category)


# ---------- 差评 → Listing 闭环 ----------

@router.post("/review-insights", response_model=ReviewInsightResponse,
             summary="差评反向改写：粘贴差评 → 主题定位 → 五点描述修复建议")
def review_insights(
    req: ReviewInsightRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 复用生成额度（feature=product_desc），免费版 5 条/天同池
    check_and_record_usage(db, user, "product_desc")
    return review_expert.analyze(req)
