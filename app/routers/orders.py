from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.models.payment import Payment
from app.routers.auth import get_current_user, get_current_user_optional
from app.services.order import OrderService
from pydantic import BaseModel
from app.models.product import Product

router = APIRouter()

class OrderCreateItem(BaseModel):
    product_id: int
    quantity: int

class ShippingAddress(BaseModel):
    full_name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    pincode: str

class OrderCreate(BaseModel):
    items: List[OrderCreateItem]
    shipping_address: ShippingAddress
    payment_method: str = "cod"
    coupon_code: Optional[str] = None

def get_order_service(session: Session = Depends(get_session)) -> OrderService:
    return OrderService(session)

@router.post("/", response_model=Order)
def create_order(
    order_in: OrderCreate, 
    current_user: Optional[User] = Depends(get_current_user_optional), 
    service: OrderService = Depends(get_order_service)
):
    user_id = None
    if current_user:
        user_id = current_user.id
    else:
        # Check if user exists by email
        existing_user = service.session.exec(select(User).where(User.email == order_in.shipping_address.email)).first()
        if existing_user:
            user_id = existing_user.id
            # Update existing user's address/phone from the order
            existing_user.address = {
                "address": order_in.shipping_address.address,
                "city": order_in.shipping_address.city,
                "state": order_in.shipping_address.state,
                "pincode": order_in.shipping_address.pincode
            }
            existing_user.phone = order_in.shipping_address.phone
            existing_user.name = order_in.shipping_address.full_name
            service.session.add(existing_user)
            service.session.commit()
            service.session.refresh(existing_user)
        else:
            # Create new guest user
            new_user = User(
                email=order_in.shipping_address.email,
                name=order_in.shipping_address.full_name,
                phone=order_in.shipping_address.phone,
                address={
                    "address": order_in.shipping_address.address,
                    "city": order_in.shipping_address.city,
                    "state": order_in.shipping_address.state,
                    "pincode": order_in.shipping_address.pincode
                },
                is_guest=True,
                is_active=True,
                password_hash="guest_account_placeholder"
            )
            service.session.add(new_user)
            service.session.commit()
            service.session.refresh(new_user)
            user_id = new_user.id

    # Convert Pydantic models to list of dicts for service
    items_data = [{"product_id": item.product_id, "quantity": item.quantity} for item in order_in.items]
    return service.create_order(
        user_id=user_id,
        items_data=items_data,
        shipping_address=order_in.shipping_address,
        payment_method=order_in.payment_method,
        coupon_code=order_in.coupon_code
    )

@router.get("/", response_model=List[Order])
def list_orders(
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    if current_user.is_superuser:
        return service.get_all_orders()
    return service.get_user_orders(current_user.id)

@router.get("/{id}")
def get_order(
    id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    order = session.get(Order, id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Check permissions - allow if guest (no login) or matches user
    if current_user and order.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Construct response with product details
    items_with_details = []
    # Explicitly load items if needed, or rely on lazy loading within session
    for item in order.items:
        product = session.get(Product, item.product_id)
        items_with_details.append({
            "id": item.product_id,
            "name": product.name if product else "Unknown Product",
            "slug": product.slug if product else None,
            "image": product.image_url if product else None,
            "images": product.full_image_urls if product else [],
            "price": item.price_at_purchase,
            "quantity": item.quantity
        })

    return {
        "orderId": str(order.id),
        "order_number": order.order_number,
        "items": items_with_details,
        "total": order.final_amount,
        "subtotal": order.total_amount,
        "discount": 0, # Simplified
        "customer": {
            "fullName": order.shipping_address.get("full_name"),
            "email": order.shipping_address.get("email"),
            "phone": order.shipping_address.get("phone"),
            "address": order.shipping_address.get("address"),
            "city": order.shipping_address.get("city"),
            "state": order.shipping_address.get("state"),
            "pincode": order.shipping_address.get("pincode"),
        },
        "status": order.order_status,
        "date": order.created_at.isoformat(),
        "paymentMethod": order.payment_type
    }

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

@router.get("/track/{order_number}")
def track_order(
    order_number: str,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
):
    """Track order by order number (e.g., PR000046)"""
    normalized_order_number = order_number.strip().upper()
    # Find order by order number (case-insensitive)
    order = session.exec(
        select(Order).where(Order.order_number == normalized_order_number)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check permissions - allow if guest (no login) or matches user or is admin
    if current_user and order.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    # For guest users, verify email matches
    if not current_user and x_user_email:
        shipping_email = order.shipping_address.get("email")
        if shipping_email != x_user_email:
            raise HTTPException(status_code=403, detail="Email does not match order")

    # Get order items with product details
    items_with_details = []
    for item in order.items:
        product = session.get(Product, item.product_id)
        items_with_details.append({
            "id": item.product_id,
            "name": product.name if product else "Unknown Product",
            "slug": product.slug if product else None,
            "image": product.image_url if product else None,
            "images": product.full_image_urls if product else [],
            "price": item.price_at_purchase,
            "quantity": item.quantity,
            "total": item.price_at_purchase * item.quantity
        })

    # Get payment/transaction details
    payments = session.exec(select(Payment).where(Payment.order_id == order.id)).all()
    payment_details = []
    for payment in payments:
        payment_details.append({
            "id": payment.id,
            "payment_id": payment.payment_id,
            "razorpay_order_id": payment.razorpay_order_id,
            "razorpay_signature": payment.razorpay_signature,
            "amount": payment.amount,
            "method": payment.payment_method.value,
            "status": payment.payment_status.value,
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat() if payment.updated_at else None
        })

    return {
        "orderId": order.id,
        "order_number": order.order_number,
        "items": items_with_details,
        "total": order.final_amount,
        "subtotal": order.total_amount,
        "discount": order.discount_amount,
        "customer": {
            "fullName": order.shipping_address.get("full_name"),
            "email": order.shipping_address.get("email"),
            "phone": order.shipping_address.get("phone"),
            "address": order.shipping_address.get("address"),
            "city": order.shipping_address.get("city"),
            "state": order.shipping_address.get("state"),
            "pincode": order.shipping_address.get("pincode"),
        },
        "status": order.order_status.value,
        "payment_status": order.payment_status.value,
        "payment_method": order.payment_type.value,
        "date": order.created_at.isoformat(),
        "tracking_id": order.tracking_id,
        "payments": payment_details
    }
