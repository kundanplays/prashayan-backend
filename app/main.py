from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import create_db_and_tables

# Import models to ensure they are registered with SQLModel metadata
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.history import LoginHistory, SearchHistory
from app.models.payment import Payment
from app.models.review import Review
from app.models.admin_user import AdminUser
from app.models.cart import CartItem
from app.models.coupon import Coupon, CouponUsage
from app.models.blog import Blog

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title="Prashayan API", 
    version="1.0.0", 
    lifespan=lifespan,
    description="API for Prashayan Ayurvedic Store"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Prashayan API. Visit /docs for Swagger UI."}

from app.routers import auth, products, orders, chatbot, payment, users, upload, admin, cart, homepage

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(payment.router, prefix="/api/v1/payment", tags=["payment"])
app.include_router(chatbot.router, prefix="/api/v1/chat", tags=["chatbot"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(cart.router, prefix="/api/v1/cart", tags=["cart"])
app.include_router(homepage.router, prefix="/api/v1/homepage", tags=["homepage"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# Add CORS
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
