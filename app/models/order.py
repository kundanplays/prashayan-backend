from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    status: str = Field(default="pending") # pending, paid, shipped, delivered
    total_amount: float
    tracking_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int
    price_at_purchase: float
