from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User

class OrderService:
    def __init__(self, session: Session):
        self.session = session

    def create_order(self, user_id: int, items_data: List[dict], total_amount: float, shipping_address: str) -> Order:
        # Create Order
        order = Order(
            user_id=user_id,
            total_amount=total_amount,
            status=OrderStatus.ORDERED,
            shipping_address=shipping_address,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Create Items
        for item in items_data:
            product = self.session.get(Product, item["product_id"])
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item['product_id']} not found")
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item["quantity"],
                price_at_purchase=product.price
            )
            self.session.add(order_item)
        
        self.session.commit()
        self.session.refresh(order)
        return order

    def get_user_orders(self, user_id: int) -> List[Order]:
        return self.session.exec(select(Order).where(Order.user_id == user_id)).all()

    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        return self.session.get(Order, order_id)
    
    def get_all_orders(self) -> List[Order]:
        return self.session.exec(select(Order)).all()

    def update_status(self, order_id: int, new_status: OrderStatus, tracking_id: str = None) -> Order:
        order = self.session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Basic State Machine Logic
        # Ordered -> Paid -> Shipped -> Delivered
        # Any -> Returned
        
        # In a strict system, we'd check valid transitions here.
        # e.g. if order.status == OrderStatus.DELIVERED and new_status == OrderStatus.SHIPPED: fail

        order.status = new_status
        order.updated_at = datetime.utcnow()
        if tracking_id:
            order.tracking_id = tracking_id
            
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order
