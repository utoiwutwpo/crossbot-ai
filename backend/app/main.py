"""
CrossBot AI — FastAPI 主应用
本地运行：uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import (ads, analytics, billing, customer_service, ebay,
                      listings, products, users)
from .scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()   # 7x24 监控：每日定时体检 + 风险日报
    yield
    stop_scheduler()


app = FastAPI(
    title="CrossBot AI API",
    description="跨境电商AI助手 — 产品描述生成 / AI客服 / 广告文案",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(users.router, prefix=f"{API_PREFIX}/users", tags=["users"])
app.include_router(products.router, prefix=f"{API_PREFIX}/products", tags=["products"])
app.include_router(customer_service.router, prefix=f"{API_PREFIX}/customer-service", tags=["customer-service"])
app.include_router(ads.router, prefix=f"{API_PREFIX}/ads", tags=["ads"])
app.include_router(billing.router, prefix=f"{API_PREFIX}/billing", tags=["billing"])
app.include_router(ebay.router, prefix=f"{API_PREFIX}/ebay", tags=["eBay"])
app.include_router(analytics.router, prefix=f"{API_PREFIX}/analytics", tags=["analytics"])
app.include_router(listings.router, prefix=f"{API_PREFIX}", tags=["watch"])


@app.get("/", include_in_schema=False)
def index():
    """营销主页（H10 风格：Hero + 平台墙 + 功能 + 定价预览 + FAQ）"""
    return FileResponse(Path(__file__).parent / "static" / "home.html")


@app.get("/app", include_in_schema=False)
def app_workbench():
    """工作台（登录后使用：生成/体检/客服/广告/差评改写/订阅）"""
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/pricing", include_in_schema=False)
def pricing_page():
    """定价页（四档套餐 + 功能对比表 + 计费 FAQ）"""
    return FileResponse(Path(__file__).parent / "static" / "pricing.html")


@app.get("/skills", include_in_schema=False)
def skills_page():
    """开源 Skills 展示页（GPSR 检查器 + 欧洲平台规则库，MIT）"""
    return FileResponse(Path(__file__).parent / "static" / "skills.html")


@app.get("/rules", include_in_schema=False)
def rules_page():
    """免费平台规则速查页（13 平台 SEO/社群获客资产，数据来自注册表 API）"""
    return FileResponse(Path(__file__).parent / "static" / "rules.html")


@app.get("/signin", include_in_schema=False)
def signin_page():
    """登录页（H10 风格：Google 登录 + 邮箱密码）"""
    return FileResponse(Path(__file__).parent / "static" / "signin.html")


@app.get("/signup", include_in_schema=False)
def signup_page():
    """注册页（H10 风格：Google 注册 + 邮箱密码）"""
    return FileResponse(Path(__file__).parent / "static" / "signup.html")


@app.get("/gpsr-check", include_in_schema=False)
def gpsr_landing():
    """免费 GPSR 合规体检获客落地页"""
    return FileResponse(Path(__file__).parent / "static" / "gpsr-check.html")


@app.get("/gpsr-check/pl", include_in_schema=False)
def gpsr_landing_pl():
    """波兰语落地页 — Allegro 卖家社群投放"""
    return FileResponse(Path(__file__).parent / "static" / "gpsr-check-pl.html")


@app.get("/gpsr-check/ro", include_in_schema=False)
def gpsr_landing_ro():
    """罗马尼亚语落地页 — eMAG 卖家社群投放"""
    return FileResponse(Path(__file__).parent / "static" / "gpsr-check-ro.html")


@app.get("/health", summary="健康检查")
def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "llm_mode": "mock" if not settings.llm_api_key else "live",
    }
