from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db.session import get_session
from app.models.order import Order

router = APIRouter()

class ChatRequest(BaseModel):
    order_id: int

class ChatResponse(BaseModel):
    message: str

@router.post("/status", response_model=ChatResponse)
def get_order_status(request: ChatRequest, session: Session = Depends(get_session)):
    order = session.get(Order, request.order_id)
    if not order:
        return ChatResponse(message=f"I couldn't find an order with ID #{request.order_id}. Please check your ID.")
    
    tracking_info = f" Tracking ID: {order.tracking_id}" if order.tracking_id else " No tracking info yet."
    return ChatResponse(message=f"Your order #{order.id} is currently {order.status}.{tracking_info}")
