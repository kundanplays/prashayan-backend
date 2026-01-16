from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, delete
from app.db.session import get_session
from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User
from app.routers.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_slug: str
    product_image: Optional[str]
    quantity: int
    price: float
    total: float

def get_cart_service(session: Session = Depends(get_session)) -> 'CartService':
    return CartService(session)

class CartService:
    def __init__(self, session: Session):
        self.session = session

    def get_user_cart(self, user_id: int) -> List[CartItemResponse]:
        """Get all cart items for a user with product details"""
        cart_items = self.session.exec(
            select(CartItem).where(CartItem.user_id == user_id)
        ).all()

        result = []
        for item in cart_items:
            product = self.session.get(Product, item.product_id)
            if product and product.is_active:
                result.append(CartItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=product.name,
                    product_slug=product.slug,
                    product_image=product.image_url,
                    quantity=item.quantity,
                    price=product.selling_price,
                    total=item.quantity * product.selling_price
                ))
        return result

    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1) -> CartItemResponse:
        """Add item to cart or update quantity if already exists"""
        # Check if product exists and is active
        product = self.session.get(Product, product_id)
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail="Product not found or unavailable")

        if quantity > product.stock_quantity:
            raise HTTPException(status_code=400, detail=f"Only {product.stock_quantity} items available in stock")

        # Check if item already in cart
        existing_item = self.session.exec(
            select(CartItem).where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id
            )
        ).first()

        if existing_item:
            # Update quantity
            new_quantity = existing_item.quantity + quantity
            if new_quantity > product.stock_quantity:
                raise HTTPException(status_code=400, detail=f"Cannot add more items. Only {product.stock_quantity} available")

            existing_item.quantity = new_quantity
            existing_item.updated_at = existing_item.updated_at  # Trigger update
            self.session.add(existing_item)
            item = existing_item
        else:
            # Create new cart item
            item = CartItem(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity
            )
            self.session.add(item)

        self.session.commit()
        self.session.refresh(item)

        return CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=product.name,
            product_slug=product.slug,
            product_image=product.image_url,
            quantity=item.quantity,
            price=product.selling_price,
            total=item.quantity * product.selling_price
        )

    def update_cart_item(self, user_id: int, cart_item_id: int, quantity: int) -> CartItemResponse:
        """Update cart item quantity"""
        item = self.session.get(CartItem, cart_item_id)
        if not item or item.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cart item not found")

        # Check product availability
        product = self.session.get(Product, item.product_id)
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail="Product no longer available")

        if quantity <= 0:
            # Remove item if quantity is 0 or negative
            self.session.delete(item)
            self.session.commit()
            raise HTTPException(status_code=200, detail="Item removed from cart")

        if quantity > product.stock_quantity:
            raise HTTPException(status_code=400, detail=f"Only {product.stock_quantity} items available in stock")

        item.quantity = quantity
        item.updated_at = item.updated_at  # Trigger update
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)

        return CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=product.name,
            product_slug=product.slug,
            product_image=product.image_url,
            quantity=item.quantity,
            price=product.selling_price,
            total=item.quantity * product.selling_price
        )

    def remove_from_cart(self, user_id: int, cart_item_id: int):
        """Remove item from cart"""
        item = self.session.get(CartItem, cart_item_id)
        if not item or item.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cart item not found")

        self.session.delete(item)
        self.session.commit()
        return {"message": "Item removed from cart"}

    def clear_cart(self, user_id: int):
        """Clear all items from user's cart"""
        self.session.exec(delete(CartItem).where(CartItem.user_id == user_id))
        self.session.commit()
        return {"message": "Cart cleared"}

@router.get("/", response_model=List[CartItemResponse])
def get_cart(current_user: User = Depends(get_current_user), service: CartService = Depends(get_cart_service)):
    """Get user's cart items"""
    return service.get_user_cart(current_user.id)

@router.post("/add", response_model=CartItemResponse)
def add_to_cart(
    cart_item: CartItemCreate,
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service)
):
    """Add item to cart"""
    return service.add_to_cart(current_user.id, cart_item.product_id, cart_item.quantity)

@router.put("/update/{cart_item_id}", response_model=CartItemResponse)
def update_cart_item(
    cart_item_id: int,
    cart_update: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service)
):
    """Update cart item quantity"""
    return service.update_cart_item(current_user.id, cart_item_id, cart_update.quantity)

@router.delete("/remove/{cart_item_id}")
def remove_from_cart(
    cart_item_id: int,
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service)
):
    """Remove item from cart"""
    return service.remove_from_cart(current_user.id, cart_item_id)

@router.delete("/clear")
def clear_cart(
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service)
):
    """Clear entire cart"""
    return service.clear_cart(current_user.id)