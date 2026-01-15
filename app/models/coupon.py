from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel
from enum import Enum

class CouponType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"

class Coupon(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Coupon Details
    code: str = Field(unique=True, index=True)  # e.g., "NEW99"
    description: Optional[str] = None
    
    # Discount
    coupon_type: CouponType = Field(default=CouponType.PERCENTAGE)
    discount_value: float  # Percentage (0-100) or fixed amount
    maximum_discount: Optional[float] = None  # Max discount cap for percentage coupons
    
    # Usage Limits
    usage_limit: Optional[int] = None  # Total usage limit (null = unlimited)
    usage_count: int = Field(default=0)  # Current usage count
    per_user_limit: Optional[int] = Field(default=1)  # Usage per user
    
    # Validity
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    
    # Minimum Order
    minimum_order_amount: Optional[float] = None
    
    # Status
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CouponUsage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # References
    coupon_id: int = Field(foreign_key="coupon.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    order_id: int = Field(foreign_key="order.id")
    
    # Usage Details
    discount_applied: float  # Actual discount amount applied
    
    # Timestamp
    used_at: datetime = Field(default_factory=datetime.utcnow)
