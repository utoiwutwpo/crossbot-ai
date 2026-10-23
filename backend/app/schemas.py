"""
API 请求/响应模型（Pydantic v2）
"""
from typing import List, Optional, Dict, Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

PlanType = Literal["free", "starter", "pro", "business"]
PlatformType = Literal[
    "amazon", "tiktok", "ebay", "walmart",
    "cdiscount", "otto", "allegro", "emag", "fruugo", "kaufland", "zalando", "bol",
]
LanguageType = Literal[
    "en", "de", "fr", "es", "it", "ar", "tr", "hi", "ta", "te", "bn",
    "zh", "ja", "ko", "pl", "ro", "nl",
]
ToneType = Literal["professional", "casual", "premium", "fun"]
AdPlatformType = Literal["facebook", "google", "tiktok"]


# ========== 用户 ==========
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ""
    company_name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Google Identity Services 返回的 ID token（credential）"""
    credential: str = Field(min_length=20, max_length=4096)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    plan: str
    usage_today: int
    daily_limit: int


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    company_name: str
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 产品描述 ==========
class ProductDescriptionRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    keywords: List[str] = Field(min_length=1, max_length=20)
    platform: PlatformType = "amazon"
    language: Optional[LanguageType] = None  # 缺省 → 按平台主推市场自动选择
    tone: ToneType = "professional"
    target_audience: Optional[str] = None
    unique_selling_points: Optional[List[str]] = None
    with_gpsr: bool = True  # 生成时附带 GPSR 合规块（CE 类目自动触发）


class BulletPoint(BaseModel):
    heading: str
    content: str


class ProductDescriptionResponse(BaseModel):
    id: Optional[str] = None
    platform: Optional[str] = None
    language: str = "en"
    title: str
    bullet_points: List[BulletPoint]
    description: str
    search_terms: str
    character_count: int
    platform_compliant: bool
    optimization_score: float
    violations: List[str] = []
    # GPSR 合规（CE 类目自动附带）
    gpsr_risk_level: Optional[str] = None
    gpsr_block: Optional[str] = None
    # Rufus/iZi 语义搜索适配
    semantic_score: Optional[float] = None
    semantic_gaps: List[str] = []


# ========== GPSR 合规体检 ==========
class GpsrCheckRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    keywords: List[str] = Field(min_length=1, max_length=20)
    platform: PlatformType = "amazon"
    asin: Optional[str] = Field(
        None, min_length=10, max_length=10,
        description="Amazon ASIN（可选，仅作记录与报告关联；报告判定基于标题/关键词）")


class GpsrCheckResponse(BaseModel):
    risk_level: str                       # high / medium / low
    platform: str
    ce_required: bool
    matched_categories: str
    ce_directives: List[str] = []
    required_languages: List[str] = []
    category_notes: str = ""
    checklist: List[Dict] = []
    gpsr_block: Optional[str] = None      # 免费版脱敏为 None（付费钩子）
    upsell_note: Optional[str] = None
    asin: Optional[str] = None
    data_source: str = "title_keywords"   # 如实标注：判定基于标题/关键词


# ========== 多平台市场矩阵（欧洲主打） ==========
class MarketMatrixRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    keywords: List[str] = Field(min_length=1, max_length=20)
    platforms: List[PlatformType] = Field(min_length=1, max_length=9)
    tone: ToneType = "professional"
    target_audience: Optional[str] = None
    unique_selling_points: Optional[List[str]] = None
    language: Optional[LanguageType] = None  # 指定则覆盖所有平台的默认语言


class MarketMatrixResponse(BaseModel):
    product_name: str
    requested: int
    succeeded: int
    results: List[ProductDescriptionResponse]
    errors: List[Dict] = []


# ========== AI 客服 ==========
class CustomerServiceRequest(BaseModel):
    customer_message: str = Field(min_length=1, max_length=4000)
    order_id: Optional[str] = None


class CustomerServiceResponse(BaseModel):
    reply: str
    intent: str
    sentiment: str
    confidence: float
    needs_escalation: bool
    escalation_reason: Optional[str] = None
    # 政策安全红线层：命中的威胁类型 + 红线说明
    policy_flags: List[str] = []
    guardrail: Optional[str] = None


# ========== 平台属性树校验 ==========
class AttributeValidateRequest(BaseModel):
    platform: PlatformType
    category: str = "generic"
    attributes: Dict[str, str] = {}


class AttributeValidateResponse(BaseModel):
    platform: str
    category: str
    missing: List[Dict] = []
    invalid: List[Dict] = []
    blockers: List[str] = []
    ready_to_list: bool
    completeness: float
    checked_total: int


# ========== 差评 → Listing 闭环 ==========
class ReviewInsightRequest(BaseModel):
    reviews: List[str] = Field(min_length=1, max_length=20,
                               description="粘贴的差评原文（1-20 条）")
    rating: Optional[int] = Field(None, ge=1, le=5, description="平均星级（可选）")
    material: Optional[str] = None
    battery_life: Optional[str] = None
    compatibility: Optional[str] = None


class ReviewInsightResponse(BaseModel):
    reviews_analyzed: int
    sentiment: str
    themes: List[Dict] = []          # theme/evidence/severity/listing_action/bullet_fix
    improved_bullets: List[BulletPoint] = []
    summary: str


# ========== 埋点 ==========
class AnalyticsTrackRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=40)
    platform: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    meta: Dict = {}


# ========== 广告文案 ==========
class AdCopyRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    platform: AdPlatformType = "facebook"
    target_audience: str = Field(min_length=1, max_length=200)
    unique_selling_point: str = Field(min_length=1, max_length=300)
    tone: str = "persuasive"
    language: LanguageType = "en"


class AdCopyResponse(BaseModel):
    primary_text: str
    headline: str
    description: str
    cta: str
    hashtags: List[str]
    character_counts: Dict[str, int]


# ========== 订阅 ==========
class SubscriptionCreate(BaseModel):
    plan: Literal["starter", "pro", "business"]


class SubscriptionInfo(BaseModel):
    plan: str
    stripe_status: str
    monthly_price_usd: Optional[float] = None
    usage_today: int
    daily_limit: int
    monthly_limit: Optional[int] = None
