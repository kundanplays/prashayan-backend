from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON, Text

class Blog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Author
    author_id: int = Field(foreign_key="user.id", index=True)  # Admin user who wrote it
    author_name: str  # Display name
    
    # Content
    title: str = Field(index=True)
    slug: str = Field(unique=True, index=True)  # URL-friendly title
    description: str  # Short excerpt/summary
    content: str = Field(sa_column=Column(Text))  # Full blog content (markdown/HTML)
    
    # Images
    image_urls: List[str] = Field(default=[], sa_column=Column(JSON))  # Multiple images
    thumbnail_url: Optional[str] = None  # Main thumbnail for listing
    
    # Categorization
    category: Optional[str] = None  # e.g., "Wellness", "Herbs", "Lifestyle"
    tags: List[str] = Field(default=[], sa_column=Column(JSON))  # e.g., ["shilajit", "energy"]
    
    # SEO
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    
    # Status
    is_published: bool = Field(default=False)
    published_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
