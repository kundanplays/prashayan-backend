from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class CartItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # References
    user_id: int = Field(foreign_key="user.id", index=True)
    product_id: int = Field(foreign_key="product.id")
    
    # Cart Details
    quantity: int = Field(default=1, ge=1)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
