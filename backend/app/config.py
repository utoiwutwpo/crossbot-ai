"""
CrossBot AI — 全局配置
所有敏感信息从环境变量 / .env 读取，绝不硬编码。
"""
import os
from pydantic_settings import BaseSettings
from pathlib import Path

# .env 位置：backend/.env（不存在时全部走默认值，方便本地零配置跑通）
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # ===== AI（智谱 GLM-4，OpenAI 兼容接口）=====
    llm_api_key: str = ""  # 为空 → Mock 模式（本地开发/测试无需 Key）
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    llm_model: str = "glm-4-plus"

    # ===== 数据库 =====
    # 默认 SQLite（本地零配置）；上线换 Supabase PostgreSQL
    database_url: str = f"sqlite:///{Path(__file__).resolve().parent.parent / 'crossbot.db'}"

    # ===== 认证 =====
    jwt_secret: str = "dev-secret-change-me-before-production"
    jwt_expire_days: int = 30

    # ===== Google 登录（OAuth2 / Google Identity Services）=====
    # 为空 → Google 按钮显示"未配置"提示；填入后前端自动加载 GIS 弹窗
    google_client_id: str = ""

    # ===== 管理端点（埋点漏斗 /analytics/summary）=====
    # 上线前务必改成强随机值
    admin_token: str = ""

    # ===== 支付（Stripe，上线时填）=====
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""

    # ===== Listing 监控（Phase 1：每日定时体检 + 风险日报）=====
    watch_scheduler_enabled: bool = True   # 上线后如用外部 cron 可关闭
    watch_daily_hour: int = 8              # 每日体检时间（UTC 小时）
    # SMTP（不配置则日报只入库不发邮件）
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_ssl: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # ===== 应用 =====
    app_name: str = "CrossBot AI"
    app_url: str = "http://localhost:8000"
    cors_origins: str = "*"  # 生产改为具体域名

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# 兼容 SQLite 的 check_same_thread
if settings.database_url.startswith("sqlite"):
    os.environ.setdefault("SQLALCHEMY_WARN_20", "0")
