from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # References
    product_id: int = Field(foreign_key="product.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    
    # Review Content
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    review_text: Optional[str] = None  # Review comment
    
    # Images
    image_url: Optional[str] = None  # Single review image
    
    # Moderation
    approved: bool = Field(default=False)  # Admin approval required
    approved_by: Optional[int] = Field(default=None, foreign_key="user.id")  # Admin who approved
    approved_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
