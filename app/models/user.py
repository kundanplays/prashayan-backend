from typing import Optional
from sqlmodel import Field, SQLModel, Column
from pydantic import computed_field
from sqlalchemy import JSON
from datetime import datetime
from app.core.config import settings

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Basic Info
    name: Optional[str] = None
    email: str = Field(unique=True, index=True)
    phone: Optional[str] = Field(default=None, index=True)
    password_hash: str
    
    # Address stored as JSON dict with keys: address, city, state, pincode
    address: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Profile
    image_url: Optional[str] = None
    
    # Account Status
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    is_guest: bool = Field(default=False)
    
    # OTP & Reset
    otp_code: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    reset_token: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Computed fields for frontend parity
    @computed_field
    @property
    def full_image_url(self) -> Optional[str]:
        if not self.image_url:
            return None
        if self.image_url.startswith(("http://", "https://", "/images/", "/")):
            return self.image_url
        return f"{settings.S3_BASE_URL}/{self.image_url}"
