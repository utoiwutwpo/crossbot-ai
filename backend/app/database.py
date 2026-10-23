"""
数据库会话与表结构定义（SQLAlchemy ORM）
本地默认 SQLite，生产切换 PostgreSQL 只需改 DATABASE_URL。
"""
from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean, Text, DateTime, Date,
    Float, ForeignKey, JSON,
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, relationship

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def gen_id() -> str:
    return uuid4().hex


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=gen_id)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    company_name = Column(String(255), default="")
    plan = Column(String(20), default="free")  # free / starter / pro / business
    stripe_customer_id = Column(String(255), default="")
    stripe_subscription_id = Column(String(255), default="")
    stripe_status = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    descriptions = relationship("ProductDescription", back_populates="user",
                                cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user",
                              cascade="all, delete-orphan")


class ProductDescription(Base):
    __tablename__ = "product_descriptions"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    product_name = Column(String(255))
    platform = Column(String(50))
    language = Column(String(10), default="en")
    tone = Column(String(20), default="professional")
    title = Column(Text)
    bullet_points = Column(JSON)
    description = Column(Text)
    search_terms = Column(String(1000))
    optimization_score = Column(Float, default=0)
    platform_compliant = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="descriptions")


class CustomerServiceConversation(Base):
    __tablename__ = "cs_conversations"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    customer_message = Column(Text)
    ai_response = Column(Text)
    intent = Column(String(30), default="other")
    sentiment = Column(String(20), default="neutral")
    needs_escalation = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdCopy(Base):
    __tablename__ = "ad_copies"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    platform = Column(String(50))  # facebook / google / tiktok
    product_name = Column(String(255))
    primary_text = Column(Text)
    headline = Column(String(200))
    ad_description = Column(Text)
    cta = Column(String(100))
    hashtags = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(String(32), primary_key=True, default=gen_id)
    user_id = Column(String(32), ForeignKey("users.id", ondelete="CASCADE"),
                     index=True, nullable=False)
    feature = Column(String(50))          # product_desc / customer_service / ad_copy
    log_date = Column(Date, default=date.today, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="usage_logs")


class AnalyticsEvent(Base):
    """验证闭环埋点：landing_view → guest_check → signup → generate → upgrade"""
    __tablename__ = "analytics_events"

    id = Column(String(32), primary_key=True, default=gen_id)
    event_type = Column(String(40), index=True, nullable=False)
    platform = Column(String(50), default="")
    utm_source = Column(String(100), default="")    # reddit / wb_zyb / fb_group_pl ...
    utm_medium = Column(String(100), default="")
    utm_campaign = Column(String(100), default="")
    ip_hash = Column(String(16), default="")        # 匿名：仅哈希前16位
    user_id = Column(String(32), index=True, default="")  # 注册后可关联
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
