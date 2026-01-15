from typing import Optional, List
from sqlmodel import Field, SQLModel, Column
from pydantic import computed_field
from sqlalchemy import JSON
from datetime import datetime
from app.core.config import settings

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Basic Info
    name: str = Field(index=True)
    slug: str = Field(index=True, unique=True)
    
    # Images
    image_urls: List[str] = Field(default=[], sa_column=Column(JSON))
    thumbnail_url: Optional[str] = None
    
    # Detailed Product Info
    ingredients: Optional[str] = None
    description: str
    benefits: Optional[str] = None
    how_to_use: Optional[str] = None
    
    # Pricing
    mrp: float
    selling_price: float
    
    # Inventory
    stock_quantity: int
    
    # Metadata
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # Computed fields for frontend parity
    @computed_field
    @property
    def price(self) -> float:
        return self.selling_price

    @computed_field
    @property
    def image_url(self) -> Optional[str]:
        if not self.thumbnail_url:
            return None
        if self.thumbnail_url.startswith(("http://", "https://")):
            return self.thumbnail_url
        # Force S3 URL by prepending base URL, stripping leading slash
        key = self.thumbnail_url.lstrip("/")
        return f"{settings.S3_BASE_URL}/{key}"

    @computed_field
    @property
    def full_image_urls(self) -> List[str]:
        urls = []
        for url in self.image_urls:
            if url.startswith(("http://", "https://")):
                urls.append(url)
            else:
                # Force S3 URL
                key = url.lstrip("/")
                urls.append(f"{settings.S3_BASE_URL}/{key}")
        return urls
