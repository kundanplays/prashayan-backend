from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import func, desc, and_, or_
from sqlmodel import Session, select
from datetime import datetime, timedelta
import json
from app.db.session import get_session
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem, PaymentStatus as OrderPaymentStatus
from app.models.payment import Payment, PaymentStatus as PaymentRecordStatus
from app.models.review import Review
from app.models.blog import Blog
from app.models.admin_user import AdminUser, AdminRole
from app.routers.auth import get_current_user
from app.services.s3 import s3_service
from pydantic import BaseModel

router = APIRouter()

# Pydantic models for requests/responses
class DashboardStats(BaseModel):
    totalUsers: int
    totalProducts: int
    totalOrders: int
    totalReviews: int
    totalBlogs: int
    pendingPayments: int
    monthlyRevenue: float
    monthlyGrowth: float
    recentOrders: List[Dict[str, Any]]
    recentReviews: List[Dict[str, Any]]
    topProducts: List[Dict[str, Any]]

class AdminUserCreate(BaseModel):
    user_id: int
    role: AdminRole = AdminRole.CUSTOMER_SUPPORT
    permissions: List[str] = []

class AdminUserUpdate(BaseModel):
    role: Optional[AdminRole] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None

class StockUpdate(BaseModel):
    stock_quantity: int

class OrderStatusUpdate(BaseModel):
    status: str

class PaymentVerify(BaseModel):
    razorpay_payment_id: str

class CancelReason(BaseModel):
    reason: str

class RoleUpdate(BaseModel):
    role: str
    permissions: List[str]

class RefundRequest(BaseModel):
    amount: float
    reason: str

def get_admin_user(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> AdminUser:
    """Get admin user with permissions check"""
    admin_user = session.exec(select(AdminUser).where(AdminUser.user_id == current_user.id)).first()
    if not admin_user:
        raise HTTPException(status_code=403, detail="Admin access required")

    if not admin_user.is_active:
        raise HTTPException(status_code=403, detail="Admin account is inactive")

    return admin_user

def check_permission(admin_user: AdminUser, permission: str) -> bool:
    """Check if admin user has specific permission"""
    if admin_user.role == AdminRole.SUPER_ADMIN:
        return True

    # Check granular permissions
    return permission in admin_user.permissions

@router.get("/permissions/check")
def check_user_permission(
    permission: str,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user)
):
    """Check if current user has specific permission"""
    has_permission = check_permission(admin_user, permission)
    return {"hasPermission": has_permission}

@router.get("/me")
def get_current_admin(
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user)
):
    """Get current admin profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": admin_user.role,
        "permissions": admin_user.permissions,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }

@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get dashboard statistics"""
    if not check_permission(admin_user, "dashboard.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Get total counts
    total_users = session.exec(select(func.count(User.id)).where(User.is_active == True)).first() or 0
    total_products = session.exec(select(func.count(Product.id)).where(Product.is_active == True)).first() or 0
    total_orders = session.exec(select(func.count(Order.id))).first() or 0
    total_reviews = session.exec(select(func.count(Review.id))).first() or 0
    total_blogs = session.exec(select(func.count(Blog.id))).first() or 0

    # Get pending payments
    pending_payments = session.exec(
        select(func.count(Payment.id)).where(Payment.payment_status == PaymentRecordStatus.PENDING)
    ).first() or 0

    # Calculate monthly revenue
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_revenue_result = session.exec(
        select(func.sum(Order.total_amount)).where(
            and_(Order.created_at >= thirty_days_ago, Order.order_status != "cancelled")
        )
    ).first()
    monthly_revenue = float(monthly_revenue_result) if monthly_revenue_result else 0.0

    # Calculate previous month revenue for growth
    sixty_days_ago = datetime.utcnow() - timedelta(days=60)
    thirty_days_ago_end = thirty_days_ago

    prev_month_revenue_result = session.exec(
        select(func.sum(Order.total_amount)).where(
            and_(
                Order.created_at >= sixty_days_ago,
                Order.created_at < thirty_days_ago_end,
                Order.order_status != "cancelled"
            )
        )
    ).first()
    prev_month_revenue = float(prev_month_revenue_result) if prev_month_revenue_result else 0.0

    # Calculate growth percentage
    monthly_growth = 0.0
    if prev_month_revenue > 0:
        monthly_growth = ((monthly_revenue - prev_month_revenue) / prev_month_revenue) * 100

    # Get recent orders
    recent_orders = session.exec(
        select(Order).order_by(desc(Order.created_at)).limit(5)
    ).all()

    recent_orders_data = []
    for order in recent_orders:
        user = session.get(User, order.user_id)
        recent_orders_data.append({
            "id": order.id,
            "user_name": user.name if user else "Unknown",
            "total_amount": float(order.total_amount),
            "status": order.order_status,
            "created_at": order.created_at.isoformat()
        })

    # Get recent reviews
    recent_reviews = session.exec(
        select(Review).order_by(desc(Review.created_at)).limit(5)
    ).all()

    recent_reviews_data = []
    for review in recent_reviews:
        user = session.get(User, review.user_id)
        product = session.get(Product, review.product_id)
        recent_reviews_data.append({
            "id": review.id,
            "user_name": user.name if user else "Unknown",
            "product_name": product.name if product else "Unknown",
            "rating": review.rating,
            "comment": review.comment[:100] + "..." if review.comment and len(review.comment) > 100 else (review.comment or ""),
            "created_at": review.created_at.isoformat()
        })

    # Get top products by sales (simplified)
    # This would ideally be an aggregation query
    top_products = []

    return DashboardStats(
        totalUsers=total_users,
        totalProducts=total_products,
        totalOrders=total_orders,
        totalReviews=total_reviews,
        totalBlogs=total_blogs,
        pendingPayments=pending_payments,
        monthlyRevenue=monthly_revenue,
        monthlyGrowth=round(monthly_growth, 2),
        recentOrders=recent_orders_data,
        recentReviews=recent_reviews_data,
        topProducts=top_products
    )

# User CRUD endpoints
@router.get("/users")
def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get all users with pagination and filters"""
    if not check_permission(admin_user, "users.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    offset = (page - 1) * limit

    # Build query
    query = select(User)

    if search:
        query = query.where(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    if status:
        is_active = status.lower() == "active"
        query = query.where(User.is_active == is_active)

    # Get total count
    total_query = query.with_only_columns(func.count(User.id))
    total = session.exec(total_query).first() or 0

    # Get paginated results
    users = session.exec(
        query.offset(offset).limit(limit).order_by(desc(User.created_at))
    ).all()

    return {
        "users": users,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get specific user"""
    if not check_permission(admin_user, "users.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@router.post("/users")
def create_user(
    user_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Create new user"""
    if not check_permission(admin_user, "users.create"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check if email exists
    existing_user = session.exec(select(User).where(User.email == user_data.get("email"))).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(**user_data)
    # In a real app, you'd hash the password here if provided
    # user.password_hash = get_password_hash(user_data["password"])
    
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    user_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update user"""
    if not check_permission(admin_user, "users.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update allowed fields
    allowed_fields = ["name", "email", "phone", "is_active"]
    for field, value in user_update.items():
        if field in allowed_fields:
            setattr(user, field, value)

    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    session.refresh(user)

    return user

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update user role"""
    if not check_permission(admin_user, "users.update_role"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # This is a bit complex as "role" implies AdminUser creation/update
    # For now, we'll assume it handles AdminUser record management
    target_admin = session.exec(select(AdminUser).where(AdminUser.user_id == user_id)).first()
    
    if role_data.role == "user":
        # Remove admin access
        if target_admin:
            session.delete(target_admin)
            session.commit()
    else:
        # Grant admin access
        if target_admin:
            target_admin.role = role_data.role
            target_admin.permissions = role_data.permissions
            session.add(target_admin)
        else:
            new_admin = AdminUser(
                user_id=user_id,
                role=role_data.role,
                permissions=role_data.permissions
            )
            session.add(new_admin)
        session.commit()
    
    return session.get(User, user_id)

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete user (soft delete by deactivating)"""
    if not check_permission(admin_user, "users.delete"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()

    return {"message": "User deactivated successfully"}

# Product CRUD endpoints
@router.get("/products")
def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get all products with pagination and filters"""
    if not check_permission(admin_user, "products.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    offset = (page - 1) * limit

    # Build query
    query = select(Product)

    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )

    if status:
        is_active = status.lower() == "active"
        query = query.where(Product.is_active == is_active)

    if category:
        query = query.where(Product.category == category)

    # Get total count
    total_query = query.with_only_columns(func.count(Product.id))
    total = session.exec(total_query).first() or 0

    # Get paginated results
    products = session.exec(
        query.offset(offset).limit(limit).order_by(desc(Product.created_at))
    ).all()

    return {
        "products": products,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get specific product"""
    if not check_permission(admin_user, "products.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product

@router.post("/products")
async def create_product(
    name: str = Form(...),
    description: str = Form(...),
    introductory_description: str = Form(None),
    mrp: float = Form(...),
    selling_price: float = Form(...),
    stock_quantity: int = Form(...),
    slug: str = Form(None),
    ingredients: str = Form(None),
    benefits: str = Form(None),
    how_to_use: str = Form(None),
    category: str = Form(None),
    is_active: bool = Form(True),
    images: List[UploadFile] = File(None),
    thumbnail_url: Optional[str] = Form(None),
    image_urls: Optional[str] = Form(None), # JSON string
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Create new product with optional image upload"""
    if not check_permission(admin_user, "products.create"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Handle Image Upload
    final_thumbnail_url = thumbnail_url

    # Parse image_urls
    final_image_urls = []
    if image_urls:
        try:
            final_image_urls = json.loads(image_urls)
            if not isinstance(final_image_urls, list):
                final_image_urls = []
        except:
            pass

    if images:
        uploaded_urls = []
        for image in images:
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="All files must be images")
            content = await image.read()
            s3_key = s3_service.upload_file(content, f"product-{image.filename}", image.content_type)
            if s3_key:
                uploaded_url = s3_service.get_public_url(s3_key)
                uploaded_urls.append(uploaded_url)

        # Put new images first, then existing images
        final_image_urls = uploaded_urls + final_image_urls
        # Set first new image as thumbnail if not already set
        if not final_thumbnail_url and uploaded_urls:
            final_thumbnail_url = uploaded_urls[0]

    # Ensure thumbnail_url is in image_urls
    if final_thumbnail_url and final_thumbnail_url not in final_image_urls:
        final_image_urls.insert(0, final_thumbnail_url)

    # Generate slug if not provided
    if not slug:
        slug = name.lower().replace(" ", "-")

    product = Product(
        name=name,
        slug=slug,
        description=description,
        introductory_description=introductory_description,
        mrp=mrp,
        selling_price=selling_price,
        stock_quantity=stock_quantity,
        ingredients=ingredients,
        benefits=benefits,
        how_to_use=how_to_use,
        category=category,
        thumbnail_url=final_thumbnail_url,
        image_urls=final_image_urls,
        is_active=is_active
    )
    
    session.add(product)
    session.commit()
    session.refresh(product)

    return product

@router.put("/products/{product_id}")
async def update_product(
    product_id: int,
    name: str = Form(None),
    description: str = Form(None),
    introductory_description: str = Form(None),
    mrp: float = Form(None),
    selling_price: float = Form(None),
    stock_quantity: int = Form(None),
    ingredients: str = Form(None),
    benefits: str = Form(None),
    how_to_use: str = Form(None),
    category: str = Form(None),
    is_active: bool = Form(None),
    images: List[UploadFile] = File(None),
    thumbnail_url: Optional[str] = Form(None),
    image_urls: Optional[str] = Form(None), # JSON string
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update product"""
    if not check_permission(admin_user, "products.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if name is not None: product.name = name
    if description is not None: product.description = description
    if introductory_description is not None: product.introductory_description = introductory_description
    if mrp is not None: product.mrp = mrp
    if selling_price is not None: product.selling_price = selling_price
    if stock_quantity is not None: product.stock_quantity = stock_quantity
    if ingredients is not None: product.ingredients = ingredients
    if benefits is not None: product.benefits = benefits
    if how_to_use is not None: product.how_to_use = how_to_use
    if category is not None: product.category = category
    if is_active is not None: product.is_active = is_active
    
    # Handle explicit URL updates
    if thumbnail_url is not None:
        product.thumbnail_url = thumbnail_url

    # Handle Image Update
    final_image_urls = []
    if image_urls is not None:
        try:
            urls = json.loads(image_urls)
            if isinstance(urls, list):
                final_image_urls = urls
        except:
            pass

    # Handle new image uploads
    if images:
        new_image_urls = []
        for image in images:
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="All files must be images")
            content = await image.read()
            s3_key = s3_service.upload_file(content, f"product-{image.filename}", image.content_type)
            if s3_key:
                url = s3_service.get_public_url(s3_key)
                new_image_urls.append(url)

        # Combine existing URLs with new uploaded URLs (new images first for thumbnail)
        final_image_urls = new_image_urls + final_image_urls

    # Update image_urls if any changes were made
    if image_urls is not None or images:
        product.image_urls = final_image_urls

        # Update thumbnail: use first image from final_image_urls, or clear if no images
        if final_image_urls:
            product.thumbnail_url = final_image_urls[0]
        else:
            product.thumbnail_url = None

    product.updated_at = datetime.utcnow()
    session.add(product)
    session.commit()
    session.refresh(product)

    return product

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete product (soft delete)"""
    if not check_permission(admin_user, "products.delete"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    product.updated_at = datetime.utcnow()
    session.add(product)
    session.commit()

    return {"message": "Product deactivated successfully"}

@router.put("/products/{product_id}/stock")
def update_product_stock(
    product_id: int,
    stock_update: StockUpdate,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update product stock"""
    if not check_permission(admin_user, "products.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.stock_quantity = stock_update.stock_quantity
    product.updated_at = datetime.utcnow()
    session.add(product)
    session.commit()
    session.refresh(product)
    
    return product

# Order CRUD endpoints
@router.get("/orders")
def get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get all orders with pagination and filters"""
    if not check_permission(admin_user, "orders.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    offset = (page - 1) * limit

    # Build query
    query = select(Order)

    if status:
        query = query.where(Order.order_status == status)

    # Get total count
    total_query = query.with_only_columns(func.count(Order.id))
    total = session.exec(total_query).first() or 0

    # Get paginated results
    orders = session.exec(
        query.offset(offset).limit(limit).order_by(desc(Order.created_at))
    ).all()

    return {
        "orders": orders,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get specific order"""
    if not check_permission(admin_user, "orders.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order

@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update order status"""
    if not check_permission(admin_user, "orders.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.order_status = status_update.status
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)

    return order

@router.post("/orders/{order_id}/verify-payment")
def verify_order_payment(
    order_id: int,
    payment_data: PaymentVerify,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Verify order payment via Razorpay ID"""
    if not check_permission(admin_user, "payments.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update payment status
    order.payment_status = OrderPaymentStatus.PAID
    order.updated_at = datetime.utcnow()
    
    # You might want to store the razorpay_payment_id somewhere too if not already
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return {"message": "Payment verified successfully"}

@router.put("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    reason_data: CancelReason,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Cancel order"""
    if not check_permission(admin_user, "orders.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.order_status = "cancelled"
    order.updated_at = datetime.utcnow()
    # Log reason if you have a field for it or order history
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return order

# Review CRUD endpoints
@router.get("/reviews")
def get_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get all reviews with pagination"""
    if not check_permission(admin_user, "reviews.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    offset = (page - 1) * limit

    # Get total count
    total = session.exec(select(func.count(Review.id))).first() or 0

    # Get paginated results
    reviews = session.exec(
        select(Review).offset(offset).limit(limit).order_by(desc(Review.created_at))
    ).all()

    return {
        "reviews": reviews,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.get("/reviews/{review_id}")
def get_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get specific review"""
    if not check_permission(admin_user, "reviews.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return review

@router.put("/reviews/{review_id}")
def update_review(
    review_id: int,
    review_update: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update review"""
    if not check_permission(admin_user, "reviews.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Update allowed fields
    if "is_verified" in review_update:
        review.is_verified = review_update["is_verified"]

    review.updated_at = datetime.utcnow()
    session.add(review)
    session.commit()
    session.refresh(review)

    return review

@router.put("/reviews/{review_id}/approve")
def approve_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Approve review"""
    if not check_permission(admin_user, "reviews.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_verified = True
    session.add(review)
    session.commit()
    return review

@router.put("/reviews/{review_id}/reject")
def reject_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Reject review"""
    if not check_permission(admin_user, "reviews.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_verified = False
    session.add(review)
    session.commit()
    return review

@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete review"""
    if not check_permission(admin_user, "reviews.delete"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    session.delete(review)
    session.commit()
    return {"message": "Review deleted successfully"}

# Blog CRUD endpoints
@router.get("/blogs")
def get_blogs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get all blogs with pagination"""
    if not check_permission(admin_user, "blogs.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    offset = (page - 1) * limit

    # Get total count
    total = session.exec(select(func.count(Blog.id))).first() or 0

    # Get paginated results
    blogs = session.exec(
        select(Blog).offset(offset).limit(limit).order_by(desc(Blog.created_at))
    ).all()

    return {
        "blogs": blogs,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.get("/blogs/{blog_id}")
def get_blog(
    blog_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get specific blog"""
    if not check_permission(admin_user, "blogs.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    return blog

@router.post("/blogs")
async def create_blog(
    title: str = Form(...),
    content: str = Form(...),
    excerpt: str = Form(...),
    slug: str = Form(None),
    is_published: bool = Form(False),
    tags: str = Form("[]"), # JSON string
    image: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Create new blog"""
    if not check_permission(admin_user, "blogs.create"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Generate slug if not provided
    if not slug:
        slug = title.lower().replace(" ", "-")

    # Handle Image
    thumbnail_url = None
    if image:
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        content_bytes = await image.read()
        s3_key = s3_service.upload_file(content_bytes, f"blog-{image.filename}", image.content_type)
        if s3_key:
            thumbnail_url = s3_service.get_public_url(s3_key)

    try:
        tags_list = json.loads(tags)
    except:
        tags_list = []

    blog = Blog(
        title=title,
        slug=slug,
        description=excerpt,
        content=content,
        author_id=current_user.id,
        author_name=current_user.name or "Admin",
        thumbnail_url=thumbnail_url,
        is_published=is_published,
        tags=tags_list
    )
    session.add(blog)
    session.commit()
    session.refresh(blog)

    return blog

@router.put("/blogs/{blog_id}")
async def update_blog(
    blog_id: int,
    title: str = Form(None),
    content: str = Form(None),
    excerpt: str = Form(None),
    is_published: bool = Form(None),
    tags: str = Form(None),
    image: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update blog"""
    if not check_permission(admin_user, "blogs.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    if title is not None: blog.title = title
    if content is not None: blog.content = content
    if excerpt is not None: blog.description = excerpt
    if is_published is not None: blog.is_published = is_published
    
    if tags is not None:
        try:
            blog.tags = json.loads(tags)
        except:
            pass

    if image:
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        content_bytes = await image.read()
        s3_key = s3_service.upload_file(content_bytes, f"blog-{image.filename}", image.content_type)
        if s3_key:
            blog.thumbnail_url = s3_service.get_public_url(s3_key)

    blog.updated_at = datetime.utcnow()
    session.add(blog)
    session.commit()
    session.refresh(blog)

    return blog

@router.put("/blogs/{blog_id}/publish")
def publish_blog(
    blog_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Publish blog"""
    if not check_permission(admin_user, "blogs.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog.is_published = True
    blog.updated_at = datetime.utcnow()
    session.add(blog)
    session.commit()
    session.refresh(blog)

    return blog

@router.put("/blogs/{blog_id}/unpublish")
def unpublish_blog(
    blog_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Unpublish blog"""
    if not check_permission(admin_user, "blogs.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog.is_published = False
    blog.updated_at = datetime.utcnow()
    session.add(blog)
    session.commit()
    session.refresh(blog)

    return blog

@router.delete("/blogs/{blog_id}")
def delete_blog(
    blog_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete blog"""
    if not check_permission(admin_user, "blogs.delete"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    session.delete(blog)
    session.commit()

    return {"message": "Blog deleted successfully"}

@router.put("/blogs/{blog_id}/tags")
def update_blog_tags(
    blog_id: int,
    tags: List[str],
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update blog tags"""
    if not check_permission(admin_user, "blogs.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    blog = session.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog.tags = tags
    blog.updated_at = datetime.utcnow()
    session.add(blog)
    session.commit()
    return blog


# Payment endpoints
@router.get("/payments")
def get_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get all payments with pagination and filters"""
    if not check_permission(admin_user, "payments.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    offset = (page - 1) * limit

    # Build query
    query = select(Payment)

    if status:
        query = query.where(Payment.payment_status == PaymentRecordStatus(status))

    # Get total count
    total_query = query.with_only_columns(func.count(Payment.id))
    total = session.exec(total_query).first() or 0

    # Get paginated results
    payments = session.exec(
        query.offset(offset).limit(limit).order_by(desc(Payment.created_at))
    ).all()

    return {
        "payments": payments,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }

@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get specific payment"""
    if not check_permission(admin_user, "payments.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return payment

@router.put("/payments/{payment_id}/verify")
def verify_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Verify payment manually"""
    if not check_permission(admin_user, "payments.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.payment_status = PaymentRecordStatus.SUCCESS
    payment.updated_at = datetime.utcnow()
    session.add(payment)
    session.commit()
    session.refresh(payment)

    return payment

@router.post("/payments/{payment_id}/refund")
def refund_payment(
    payment_id: int,
    refund_data: RefundRequest,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Process refund"""
    if not check_permission(admin_user, "payments.refund"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # In a real app, call Payment Gateway API here
    
    payment.payment_status = PaymentRecordStatus.REFUNDED
    payment.updated_at = datetime.utcnow()
    session.add(payment)
    session.commit()
    session.refresh(payment)
    
    return payment

# Analytics
@router.get("/analytics/overview")
def get_analytics_overview(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get analytics overview"""
    if not check_permission(admin_user, "analytics.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Placeholder for complex analytics
    return {
        "revenue": [12000, 15000, 18000, 14000, 22000, 25000],
        "orders": [120, 150, 180, 140, 220, 250],
        "visitors": [5000, 6000, 7500, 6200, 8000, 9500],
        "conversion": [2.4, 2.5, 2.4, 2.2, 2.7, 2.6]
    }

@router.get("/analytics/revenue/{period}")
def get_revenue_analytics(
    period: str,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get revenue analytics"""
    if not check_permission(admin_user, "analytics.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "data": [1000, 2000, 1500, 3000, 2500, 4000, 3500]}

@router.get("/analytics/users/{period}")
def get_user_analytics(
    period: str,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get user analytics"""
    if not check_permission(admin_user, "analytics.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "data": [10, 20, 15, 30, 25, 40, 35]}

@router.get("/analytics/products")
def get_product_analytics(
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get product analytics"""
    if not check_permission(admin_user, "analytics.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [
        {"name": "Product A", "views": 1200, "sales": 120},
        {"name": "Product B", "views": 900, "sales": 80},
        {"name": "Product C", "views": 1500, "sales": 200},
    ]


# Settings
@router.get("/settings")
def get_settings(
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user)
):
    if not check_permission(admin_user, "settings.read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Dummy settings
    return {
        "siteName": "Prashayan",
        "supportEmail": "support@prashayan.com",
        "currency": "INR",
        "shippingFee": 50,
        "freeShippingThreshold": 1000
    }

@router.put("/settings")
def update_settings(
    settings: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user)
):
    if not check_permission(admin_user, "settings.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return settings

@router.post("/settings/reset")
def reset_settings(
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user)
):
    if not check_permission(admin_user, "settings.update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"message": "Settings reset to default"}


# Admin user management
@router.post("/admin-users")
def create_admin_user(
    admin_data: AdminUserCreate,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Create new admin user (super admin only)"""
    if admin_user.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admins can create admin users")

    # Check if user exists
    user = session.get(User, admin_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already an admin
    existing_admin = session.exec(
        select(AdminUser).where(AdminUser.user_id == admin_data.user_id)
    ).first()
    if existing_admin:
        raise HTTPException(status_code=400, detail="User is already an admin")

    new_admin = AdminUser(
        user_id=admin_data.user_id,
        role=admin_data.role,
        permissions=admin_data.permissions
    )
    session.add(new_admin)
    session.commit()
    session.refresh(new_admin)

    return new_admin

@router.get("/admin-users")
def get_admin_users(
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Get all admin users (super admin only)"""
    if admin_user.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admins can view admin users")

    admin_users = session.exec(select(AdminUser)).all()
    return admin_users

@router.put("/admin-users/{admin_id}")
def update_admin_user(
    admin_id: int,
    admin_update: AdminUserUpdate,
    current_user: User = Depends(get_current_user),
    admin_user: AdminUser = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update admin user (super admin only)"""
    if admin_user.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admins can update admin users")

    target_admin = session.get(AdminUser, admin_id)
    if not target_admin:
        raise HTTPException(status_code=404, detail="Admin user not found")

    # Update fields
    if admin_update.role is not None:
        target_admin.role = admin_update.role
    if admin_update.permissions is not None:
        target_admin.permissions = admin_update.permissions
    if admin_update.is_active is not None:
        target_admin.is_active = admin_update.is_active

    target_admin.updated_at = datetime.utcnow()
    session.add(target_admin)
    session.commit()
    session.refresh(target_admin)

    return target_admin
