from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.order import Order, OrderItem, OrderStatus
from app.services.email import format_address_for_email
from app.models.product import Product
from app.models.user import User
from app.models.coupon import Coupon, CouponUsage, CouponType
from app.services.email import send_order_success_email, send_shipping_notification_email, send_delivery_feedback_email, send_order_cancellation_email

class OrderService:
    def __init__(self, session: Session):
        self.session = session

    def validate_and_apply_coupon(self, coupon_code: str, user_id: int, subtotal: float) -> tuple[float, float, Coupon]:
        """Validate coupon and calculate discount. Returns (final_amount, discount_amount, coupon)"""
        if not coupon_code:
            return subtotal, 0.0, None

        # Find coupon
        coupon = self.session.exec(
            select(Coupon).where(Coupon.code == coupon_code.upper())
        ).first()

        if not coupon:
            raise HTTPException(status_code=400, detail="Invalid coupon code")

        if not coupon.is_active:
            raise HTTPException(status_code=400, detail="Coupon is not active")

        # Check validity period
        now = datetime.utcnow()
        if coupon.valid_from > now:
            raise HTTPException(status_code=400, detail="Coupon is not yet valid")
        if coupon.valid_until and coupon.valid_until < now:
            raise HTTPException(status_code=400, detail="Coupon has expired")

        # Check minimum order amount
        if coupon.minimum_order_amount and subtotal < coupon.minimum_order_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum order amount of ₹{coupon.minimum_order_amount} required for this coupon"
            )

        # Check usage limits
        if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
            raise HTTPException(status_code=400, detail="Coupon usage limit exceeded")

        # Check per-user limit
        user_usage_count = self.session.exec(
            select(CouponUsage).where(
                CouponUsage.coupon_id == coupon.id,
                CouponUsage.user_id == user_id
            )
        ).all()

        if coupon.per_user_limit and len(user_usage_count) >= coupon.per_user_limit:
            raise HTTPException(status_code=400, detail="You have already used this coupon the maximum allowed times")

        # Calculate discount
        if coupon.coupon_type == CouponType.PERCENTAGE:
            discount_amount = subtotal * (coupon.discount_value / 100)
            if coupon.maximum_discount:
                discount_amount = min(discount_amount, coupon.maximum_discount)
        else:  # FIXED
            discount_amount = min(coupon.discount_value, subtotal)

        final_amount = subtotal - discount_amount

        return final_amount, discount_amount, coupon

    def create_order(self, user_id: int, items_data: List[dict], shipping_address: dict, payment_method: str = "cod", coupon_code: Optional[str] = None) -> Order:
        # Calculate actual total from products (prevent frontend amount injection)
        calculated_total = 0.0
        order_items = []

        for item in items_data:
            product = self.session.get(Product, item["product_id"])
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item['product_id']} not found")

            if not product.is_active:
                raise HTTPException(status_code=400, detail=f"Product {product.name} is not available")

            if item["quantity"] > product.stock_quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")

            # Use selling_price if available, otherwise mrp
            item_price = getattr(product, 'selling_price', None) or product.mrp
            item_total = item_price * item["quantity"]
            calculated_total += item_total

            order_item = OrderItem(
                product_id=product.id,
                quantity=item["quantity"],
                price_at_purchase=item_price
            )
            order_items.append(order_item)

        # Validate and apply coupon
        final_amount, discount_amount, coupon = self.validate_and_apply_coupon(coupon_code, user_id, calculated_total)

        # Create Order with calculated amounts
        order = Order(
            user_id=user_id,
            total_amount=calculated_total,
            discount_amount=discount_amount,
            final_amount=final_amount,
            payment_type=payment_method,
            payment_status="paid" if payment_method == "online" else "unpaid",
            order_status=OrderStatus.PLACED,
            coupon_code=coupon_code.upper() if coupon_code else None,
            shipping_address={
                "full_name": shipping_address.full_name,
                "email": shipping_address.email,
                "phone": shipping_address.phone,
                "address": shipping_address.address,
                "city": shipping_address.city,
                "state": shipping_address.state,
                "pincode": shipping_address.pincode
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Create Order Items with order_id
        for order_item in order_items:
            order_item.order_id = order.id
            self.session.add(order_item)

        # Update product stock
        for item_data, order_item in zip(items_data, order_items):
            product = self.session.get(Product, item_data["product_id"])
            product.stock_quantity -= item_data["quantity"]
            self.session.add(product)

        # Update user's saved address
        user = self.session.get(User, user_id)
        if user:
            user.address = {
                "address": shipping_address.address,
                "city": shipping_address.city,
                "state": shipping_address.state,
                "pincode": shipping_address.pincode
            }
            user.phone = shipping_address.phone  # Also update phone if provided
            self.session.add(user)

        self.session.commit()
        self.session.refresh(order)

        # Track coupon usage if coupon was applied
        if coupon and discount_amount > 0:
            coupon_usage = CouponUsage(
                coupon_id=coupon.id,
                user_id=user_id,
                order_id=order.id,
                discount_applied=discount_amount
            )
            self.session.add(coupon_usage)

            # Update coupon usage count
            coupon.usage_count += 1
            self.session.add(coupon)

            self.session.commit()

        # Send order confirmation email
        try:
            # Get user details
            user = self.session.get(User, user_id)
            if user:
                # Get product details for email
                product_details = []
                for item in items_data:
                    product = self.session.get(Product, item["product_id"])
                    if product:
                        product_details.append({
                            'id': product.id,
                            'name': product.name,
                            'selling_price': getattr(product, 'selling_price', None) or product.mrp,
                            'mrp': product.mrp
                        })

                # Format order items for email
                order_items_for_email = [
                    {'product_id': item['product_id'], 'quantity': item['quantity']}
                    for item in items_data
                ]

                # Format delivery address
                delivery_address = format_address_for_email(shipping_address)

                # Send order success email
                order_date = order.created_at.strftime("%B %d, %Y at %I:%M %p")
                send_order_success_email(
                    to_email=shipping_address.email,
                    user_name=user.name,
                    order_id=order.id,
                    order_date=order_date,
                    order_items=order_items_for_email,
                    product_details=product_details,
                    subtotal=order.total_amount,
                    shipping=0.0,  # You can modify this based on your shipping logic
                    total_amount=order.total_amount,
                    delivery_address=delivery_address,
                    payment_method=payment_method
                )

        except Exception as e:
            print(f"Failed to send order confirmation email: {e}")
            # Don't fail the order creation if email fails

        return order

    def get_user_orders(self, user_id: int) -> List[Order]:
        return self.session.exec(select(Order).where(Order.user_id == user_id)).all()

    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        return self.session.get(Order, order_id)
    
    def get_all_orders(self) -> List[Order]:
        return self.session.exec(select(Order)).all()

    def update_status(self, order_id: int, new_status: OrderStatus, tracking_id: str = None) -> Order:
        order = self.session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Basic State Machine Logic
        # Ordered -> Paid -> Shipped -> Delivered
        # Any -> Returned
        
        # In a strict system, we'd check valid transitions here.
        # e.g. if order.status == OrderStatus.DELIVERED and new_status == OrderStatus.SHIPPED: fail

        order.status = new_status
        order.updated_at = datetime.utcnow()
        if tracking_id:
            order.tracking_id = tracking_id

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Send status update emails
        try:
            user = self.session.get(User, order.user_id)
            if user:
                email = order.shipping_address.get('email')
                if email:
                    if new_status == OrderStatus.SHIPPED:
                        # Send shipping notification
                        send_shipping_notification_email(
                            to_email=email,
                            user_name=user.name,
                            order_id=order.id,
                            tracking_id=tracking_id,
                            estimated_delivery="3-5 business days"  # You can customize this
                        )
                    elif new_status == OrderStatus.DELIVERED:
                        # Send delivery feedback email
                        # Get order items summary for the email
                        order_items = self.session.exec(
                            select(OrderItem).where(OrderItem.order_id == order.id)
                        ).all()

                        items_summary = ""
                        for item in order_items:
                            product = self.session.get(Product, item.product_id)
                            if product:
                                items_summary += f"• {product.name} x {item.quantity}<br>"

                        delivery_date = datetime.utcnow().strftime("%B %d, %Y")
                        send_delivery_feedback_email(
                            to_email=email,
                            user_name=user.name,
                            order_id=order.id,
                            delivery_date=delivery_date,
                            order_items_summary=items_summary,
                            feedback_url=f"http://localhost:3000/feedback/{order.id}"  # Adjust URL as needed
                        )
                    elif new_status == OrderStatus.CANCELLED:
                        # Send cancellation email
                        # Get order items summary for the email
                        order_items = self.session.exec(
                            select(OrderItem).where(OrderItem.order_id == order.id)
                        ).all()

                        items_summary = ""
                        for item in order_items:
                            product = self.session.get(Product, item.product_id)
                            if product:
                                items_summary += f"• {product.name} x {item.quantity}<br>"

                        send_order_cancellation_email(
                            to_email=email,
                            user_name=user.name,
                            order_id=order.id,
                            cancellation_reason="Order cancelled by admin",  # You can pass this as parameter
                            order_items_summary=items_summary,
                            total_amount=order.total_amount
                        )

        except Exception as e:
            print(f"Failed to send status update email: {e}")
            # Don't fail the status update if email fails

        return order
