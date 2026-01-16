from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from app.db.session import get_session
from app.models.product import Product
from app.models.blog import Blog
from app.models.user import User
from app.routers.auth import get_current_user_optional
from pydantic import BaseModel

router = APIRouter()

class HomepageData(BaseModel):
    featured_products: List[Dict[str, Any]]
    categories: List[str]
    recent_blogs: List[Dict[str, Any]]
    stats: Dict[str, int]

class CategoryData(BaseModel):
    name: str
    product_count: int
    image: Optional[str]

@router.get("/", response_model=HomepageData)
def get_homepage_data(
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: Session = Depends(get_session)
):
    """Get homepage data including featured products, categories, and blogs"""

    # Get featured products (first 6 products)
    featured_products_query = session.exec(
        select(Product).where(Product.is_active == True).limit(6)
    ).all()

    featured_products = []
    for product in featured_products_query:
        featured_products.append({
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "price": product.price,
            "mrp": product.mrp,
            "image_url": product.image_url,
            "thumbnail_url": product.thumbnail_url
        })

    # Get categories (extract from product descriptions or use predefined)
    # For now, use some common Ayurvedic categories
    categories = [
        "Shilajit & Rasayanas",
        "Herbal Supplements",
        "Ayurvedic Teas",
        "Skin Care",
        "Digestive Health",
        "Immunity Boosters"
    ]

    # Get recent blogs (published ones)
    recent_blogs_query = session.exec(
        select(Blog).where(Blog.is_published == True).order_by(Blog.published_at.desc()).limit(3)
    ).all()

    recent_blogs = []
    for blog in recent_blogs_query:
        recent_blogs.append({
            "id": blog.id,
            "title": blog.title,
            "slug": blog.slug,
            "description": blog.description,
            "thumbnail_url": blog.thumbnail_url,
            "published_at": blog.published_at.isoformat() if blog.published_at else None
        })

    # Get stats
    total_products = session.exec(
        select(func.count(Product.id)).where(Product.is_active == True)
    ).first() or 0

    total_users = session.exec(
        select(func.count(User.id)).where(User.is_active == True)
    ).first() or 0

    total_blogs = session.exec(
        select(func.count(Blog.id)).where(Blog.is_published == True)
    ).first() or 0

    stats = {
        "total_products": total_products,
        "total_users": total_users,
        "total_blogs": total_blogs
    }

    return HomepageData(
        featured_products=featured_products,
        categories=categories,
        recent_blogs=recent_blogs,
        stats=stats
    )

@router.get("/categories", response_model=List[str])
def get_categories(session: Session = Depends(get_session)):
    """Get available product categories"""
    # For now, return predefined categories
    # In a real app, you might extract these from product tags or categories
    return [
        "Shilajit & Rasayanas",
        "Herbal Supplements",
        "Ayurvedic Teas",
        "Skin Care",
        "Digestive Health",
        "Immunity Boosters",
        "Wellness",
        "Anti-Aging"
    ]

@router.get("/featured-products", response_model=List[Dict[str, Any]])
def get_featured_products(
    limit: int = 8,
    session: Session = Depends(get_session)
):
    """Get featured products for homepage"""
    products_query = session.exec(
        select(Product).where(Product.is_active == True).limit(limit)
    ).all()

    featured_products = []
    for product in products_query:
        featured_products.append({
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "price": product.price,
            "mrp": product.mrp,
            "image_url": product.image_url,
            "thumbnail_url": product.thumbnail_url,
            "discount_percentage": round(((product.mrp - product.selling_price) / product.mrp) * 100) if product.mrp > product.selling_price else 0
        })

    return featured_products