from typing import Optional
from sqlmodel import Field, SQLModel

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(index=True, unique=True)
    description: str
    price: float
    stock_quantity: int
    image_url: Optional[str] = None
