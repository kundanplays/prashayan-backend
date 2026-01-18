from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Enum as SAEnum
from enum import Enum

class PaymentMethod(str, Enum):
    RAZORPAY = "razorpay"
    COD = "cod"
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"

class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # References
    order_id: int = Field(foreign_key="order.id", index=True)
    
    # Payment Gateway Info
    payment_id: Optional[str] = None  # Razorpay payment ID
    razorpay_order_id: Optional[str] = None  # Razorpay order ID
    razorpay_signature: Optional[str] = None  # For verification
    
    # Payment Details
    amount: float
    payment_method: PaymentMethod
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        sa_column=Column(SAEnum(PaymentStatus, values_callable=lambda x: [e.value for e in x]))
    )
    
    # Metadata
    error_message: Optional[str] = None  # For failed payments
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
