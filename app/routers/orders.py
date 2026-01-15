from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db.session import get_session
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.order import OrderService
from pydantic import BaseModel

router = APIRouter()

class OrderCreateItem(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderCreateItem]
    total_amount: float
    shipping_address: str

def get_order_service(session: Session = Depends(get_session)) -> OrderService:
    return OrderService(session)

@router.post("/", response_model=Order)
def create_order(
    order_in: OrderCreate, 
    current_user: User = Depends(get_current_user), 
    service: OrderService = Depends(get_order_service)
):
    # Convert Pydantic models to list of dicts for service
    items_data = [{"product_id": item.product_id, "quantity": item.quantity} for item in order_in.items]
    return service.create_order(
        user_id=current_user.id,
        items_data=items_data,
        total_amount=order_in.total_amount,
        shipping_address=order_in.shipping_address
    )

@router.get("/", response_model=List[Order])
def list_orders(
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    if current_user.is_superuser:
        return service.get_all_orders()
    return service.get_user_orders(current_user.id)

@router.patch("/{id}/status", response_model=Order)
def update_order_status(
    id: int, 
    status: OrderStatus, 
    tracking_id: str = None,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return service.update_status(id, status, tracking_id)
