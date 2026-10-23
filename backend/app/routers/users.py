"""用户注册 / 登录 / 信息（含 Google OAuth 登录）"""
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db, User
from ..schemas import UserCreate, UserLogin, GoogleAuthRequest, TokenResponse, UserOut
from ..auth import hash_password, verify_password, create_access_token, get_current_user
from ..billing import plan_config, usage_today
from .analytics import track_event

router = APIRouter()


@router.post("/register", response_model=TokenResponse, summary="注册并直接登录")
def register(
    body: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="该邮箱已注册")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name or "",
        company_name=body.company_name or "",
        plan="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # 验证闭环埋点：signup + 渠道归因（utm 从前端注册表单/落地页带来）
    track_event(db, "signup", request, user_id=user.id,
                utm_source=utm_source, utm_medium=utm_medium,
                utm_campaign=utm_campaign)
    cfg = plan_config(user.plan)
    return TokenResponse(
        access_token=create_access_token(user.id),
        plan=user.plan,
        usage_today=0,
        daily_limit=cfg["daily_limit"],
    )


@router.post("/login", response_model=TokenResponse, summary="登录")
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    cfg = plan_config(user.plan)
    return TokenResponse(
        access_token=create_access_token(user.id),
        plan=user.plan,
        usage_today=usage_today(db, user.id),
        daily_limit=cfg["daily_limit"],
    )


@router.get("/me", response_model=UserOut, summary="当前用户信息")
def me(user: User = Depends(get_current_user)):
    return user


# ---------- Google 登录（Sign up / Log in with Google） ----------

@router.get("/google-config", summary="Google 登录可用性与前端 Client ID")
def google_config():
    """未配置 GOOGLE_CLIENT_ID 时 enabled=false，前端按钮给出引导提示而非报错。"""
    return {"enabled": bool(settings.google_client_id), "client_id": settings.google_client_id}


@router.post("/google", response_model=TokenResponse, summary="Google ID token 登录/注册（自动关联同邮箱账号）")
async def google_auth(body: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google 登录未启用：请在 backend/.env 配置 GOOGLE_CLIENT_ID")

    # 服务端校验 ID token（Google tokeninfo 会验签 + 返回 aud/exp/email_verified）
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://oauth2.googleapis.com/tokeninfo",
                                 params={"id_token": body.credential})
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="无法连接 Google 校验服务，请稍后再试")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Google 凭证无效或已过期")
    info = r.json()
    if info.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=401, detail="Google 凭证与本站不匹配（aud 校验失败）")
    if info.get("email_verified") not in ("true", True):
        raise HTTPException(status_code=401, detail="Google 邮箱未验证")

    email = info["email"]
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Google 账号没有密码：hash 一个随机 uuid，密码登录永远不可通过
        user = User(
            email=email,
            password_hash=hash_password(uuid.uuid4().hex + uuid.uuid4().hex),
            full_name=info.get("name", ""),
            plan="free",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    cfg = plan_config(user.plan)
    return TokenResponse(
        access_token=create_access_token(user.id),
        plan=user.plan,
        usage_today=usage_today(db, user.id),
        daily_limit=cfg["daily_limit"],
    )
