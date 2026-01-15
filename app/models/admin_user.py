from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON
from enum import Enum

class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"  # Full access
    PRODUCT_MANAGER = "product_manager"  # Manage products
    ORDER_MANAGER = "order_manager"  # Manage orders
    CONTENT_MANAGER = "content_manager"  # Manage blogs, reviews
    CUSTOMER_SUPPORT = "customer_support"  # View only, update order status

class AdminUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Link to main User table
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    
    # Role & Permissions
    role: AdminRole = Field(default=AdminRole.CUSTOMER_SUPPORT)
    
    # Granular Permissions (list of permission strings)
    # e.g., ["products.create", "products.update", "products.delete", "orders.view", "orders.update"]
    permissions: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Status
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
