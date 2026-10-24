"""
eBay 接入路由：OAuth 授权 + Webhook 接收 + 回复管理
"""
from fastapi import APIRouter, Request, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database import get_db, User, IncomingMessage, OutgoingReply, eBayConnection
from ..auth import get_current_user
from ..ebay_service import eBayService
from ..billing import check_and_record_usage

router = APIRouter(prefix="/ebay", tags=["eBay 接入"])
ebay_svc = eBayService()


@router.get("/auth-url", summary="获取 eBay OAuth 授权 URL")
def get_ebay_auth_url(user: User = Depends(get_current_user)):
    """
    前端调用此接口拿到授权 URL，跳转到 eBay OAuth 页
    卖家登录后 eBay 回调 /ebay/oauth/callback
    """
    import secrets
    state = secrets.token_urlsafe(32)
    # TODO: 把 state 存到 session/DB 防 CSRF
    auth_url = ebay_svc.build_auth_url(state)
    return {"auth_url": auth_url, "state": state}


@router.get("/oauth/callback", summary="eBay OAuth 回调")
async def ebay_oauth_callback(
    code: str,
    state: str,
    error: str = None,
    db: Session = Depends(get_db),
):
    """
    eBay OAuth 回调接口：
    - 有 error 参数 → 授权失败
    - 有 code 参数 → 用 code 换 token
    """
    if error:
        raise HTTPException(status_code=400, detail=f"eBay 授权失败：{error}")

    # 从 session 或 cookie 取 user_id（这里简化：通过 query param 或 header）
    # 生产环境：用 session 绑定
    user_id = None  # TODO: 从请求上下文取

    if not user_id:
        raise HTTPException(status_code=401, detail="未登录或 session 无效")

    result = await ebay_svc.exchange_code_for_tokens(code, user_id)
    return {"success": True, "message": "eBay 授权成功"}


@router.post("/webhook/message", summary="eBay 买家消息 webhook")
async def ebay_message_webhook(
    request: Request,
    x_ebay_credentials_match: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    eBay 推送买家消息到 CrossBot
    需配置 webhook subscription，指向此端点
    """
    # 验签（简化版）
    if not x_ebay_credentials_match:
        raise HTTPException(status_code=401, detail="缺少 eBay 签名验证")

    # 从请求体解析消息
    payload = await request.json()

    # 从 payload 或 header 取 user_id（eBay 会带 marketplace 信息）
    user_id = payload.get("user_id") or payload.get("application", {}).get("sellerUserId")
    if not user_id:
        raise HTTPException(status_code=400, detail="无法确定卖家身份")

    # 检查授权状态
    conn = db.query(EBayConnection).filter_by(user_id=user_id).first()
    if not conn:
        raise HTTPException(status_code=403, detail="eBay 未授权，请先连接 eBay")

    # 处理消息
    result = await ebay_svc.handle_webhook_message(user_id, payload, db)
    return result


@router.get("/messages", summary="查看收到的 eBay 消息")
def list_ebay_messages(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页列出买家的 eBay 消息及 AI 回复草稿"""
    q = (
        db.query(IncomingMessage)
        .filter(IncomingMessage.user_id == user.id)
        .order_by(IncomingMessage.created_at.desc())
    )
    if status:
        q = q.filter(IncomingMessage.status == status)

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": m.id,
                "buyer_id": m.buyer_id,
                "thread_id": m.thread_id,
                "customer_message": m.customer_message,
                "status": m.status,
                "created_at": m.created_at,
                "ai_reply": m.reply.ai_reply if m.reply else None,
                "reply_status": m.reply.status if m.reply else None,
                "needs_escalation": m.reply.needs_escalation if m.reply else False,
            }
            for m in items
        ],
    }


@router.post("/replies/{reply_id}/send", summary="发送 AI 回复给买家")
async def send_ebay_reply(
    reply_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    卖家确认 AI 回复后，点击发送按钮
    调用 eBay API 把回复发给买家
    """
    result = await ebay_svc.send_reply(reply_id, user.id)
    return result


@router.get("/connection/status", summary="查看 eBay 授权状态")
def get_ebay_connection_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = db.query(EBayConnection).filter_by(user_id=user.id).first()
    if not conn:
        return {"connected": False}
    return {
        "connected": True,
        "expires_at": conn.expires_at,
        "marketplace_id": conn.marketplace_id,
    }
