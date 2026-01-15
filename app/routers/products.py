from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.product import Product
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[Product])
def read_products(session: Session = Depends(get_session)):
    return session.exec(select(Product)).all()

@router.get("/{slug}", response_model=Product)
def read_product(slug: str, session: Session = Depends(get_session)):
    product = session.exec(select(Product).where(Product.slug == slug)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=Product)
def create_product(product: Product, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    session.add(product)
    session.commit()
    session.refresh(product)
    return product
