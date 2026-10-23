"""AI 客服消息处理与对话记录"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db, User, CustomerServiceConversation
from ..schemas import CustomerServiceRequest, CustomerServiceResponse
from ..auth import get_current_user
from ..experts.customer_service import CustomerServiceExpert
from ..billing import check_and_record_usage

router = APIRouter()
expert = CustomerServiceExpert()


@router.post("/messages", response_model=CustomerServiceResponse,
             summary="处理一条买家咨询")
def handle_message(
    req: CustomerServiceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_and_record_usage(db, user, "customer_service")
    result = expert.handle(req)
    db.add(CustomerServiceConversation(
        user_id=user.id,
        customer_message=req.customer_message,
        ai_response=result.reply,
        intent=result.intent,
        sentiment=result.sentiment,
        needs_escalation=result.needs_escalation,
    ))
    db.commit()
    return result


@router.get("/conversations", summary="对话历史（分页）")
def list_conversations(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(CustomerServiceConversation)
        .filter(CustomerServiceConversation.user_id == user.id)
        .order_by(CustomerServiceConversation.created_at.desc())
    )
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": r.id,
                "customer_message": r.customer_message,
                "ai_response": r.ai_response,
                "intent": r.intent,
                "sentiment": r.sentiment,
                "needs_escalation": r.needs_escalation,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
