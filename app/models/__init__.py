# Import all models to register them with SQLModel
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem, OrderStatus, PaymentType, PaymentStatus
from app.models.history import LoginHistory, SearchHistory
from app.models.payment import Payment, PaymentMethod
from app.models.review import Review
from app.models.admin_user import AdminUser, AdminRole
from app.models.cart import CartItem
from app.models.coupon import Coupon, CouponUsage, CouponType
from app.models.blog import Blog

__all__ = [
    "User",
    "Product",
    "Order",
    "OrderItem",
    "OrderStatus",
    "PaymentType",
    "PaymentStatus",
    "LoginHistory",
    "SearchHistory",
    "Payment",
    "PaymentMethod",
    "Review",
    "AdminUser",
    "AdminRole",
    "CartItem",
    "Coupon",
    "CouponUsage",
    "CouponType",
    "Blog",
]
