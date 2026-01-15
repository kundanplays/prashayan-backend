from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel, Column
from sqlalchemy import JSON
from enum import Enum

class PaymentType(str, Enum):
    COD = "cod"
    ONLINE = "online"

class PaymentStatus(str, Enum):
    PAID = "paid"
    UNPAID = "unpaid"
    PENDING = "pending"
    FAILED = "failed"

class OrderStatus(str, Enum):
    PLACED = "placed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURNED = "returned"
    CANCELLED = "cancelled"

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int
    price_at_purchase: float

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    
    # Order Details
    total_amount: float
    discount_amount: float = Field(default=0.0)
    final_amount: float
    
    # Payment Info
    payment_type: PaymentType = Field(default=PaymentType.ONLINE)
    payment_status: PaymentStatus = Field(default=PaymentStatus.UNPAID)
    
    # Order Status
    order_status: OrderStatus = Field(default=OrderStatus.PLACED)
    
    # Shipping
    tracking_id: Optional[str] = None
    shipping_address: dict = Field(sa_column=Column(JSON))
    
    # Coupon
    coupon_code: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    items: List["OrderItem"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})
