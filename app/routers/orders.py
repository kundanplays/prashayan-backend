from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.order import Order, OrderItem
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=Order)
def create_order(order: Order, items: List[OrderItem], current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    order.user_id = current_user.id
    session.add(order)
    session.commit()
    session.refresh(order)
    
    for item in items:
        item.order_id = order.id
        session.add(item)
    
    session.commit()
    return order

@router.get("/me", response_model=List[Order])
def read_my_orders(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(Order).where(Order.user_id == current_user.id)).all()

@router.get("/", response_model=List[Order])
def read_all_orders(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    return session.exec(select(Order)).all()

@router.patch("/{id}/status", response_model=Order)
def update_order_status(id: int, status: str, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    order = session.get(Order, id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order.status = status
    session.add(order)
    session.commit()
    session.refresh(order)
    return order
