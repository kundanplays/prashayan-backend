from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.product import Product
from app.routers.auth import get_current_user, get_current_user_optional
from app.models.user import User

router = APIRouter()

from app.services.history import HistoryService
from sqlmodel import or_

def get_history_service(session: Session = Depends(get_session)) -> HistoryService:
    return HistoryService(session)

@router.get("/", response_model=List[Product])
def read_products(
    q: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional), # Optional auth for tracking
    session: Session = Depends(get_session),
    history_service: HistoryService = Depends(get_history_service)
):
    if q:
        # Log Search
        user_id = current_user.id if current_user else None
        history_service.log_search(query=q, user_id=user_id)
        
        # Filter Products
        return session.exec(select(Product).where(
            or_(
                Product.name.ilike(f"%{q}%"),
                Product.description.ilike(f"%{q}%")
            )
        )).all()
        
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
