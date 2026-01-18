import razorpay
import hmac
import hashlib
import json
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from app.core.config import settings
from app.db.session import get_session
from sqlmodel import Session, select
from app.models.order import Order, PaymentStatus as OrderPaymentStatus
from app.services.email import send_order_success_email, format_address_for_email, format_order_items_for_email
from app.models.user import User
from app.models.payment import Payment, PaymentStatus, PaymentMethod

router = APIRouter()

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@router.post("/create-order")
async def create_payment_order(
    amount: float,
    order_id: int = None,
    session: Session = Depends(get_session)
):
    # Amount needed in paise
    data = {"amount": int(amount * 100), "currency": "INR", "payment_capture": 1}

    # Add notes if order_id is provided
    if order_id:
        data["notes"] = {"internal_order_id": str(order_id)}

    try:
        payment = client.order.create(data=data)

        # Store Razorpay order ID for tracking
        if order_id:
            payment_record = session.exec(
                select(Payment).where(Payment.order_id == order_id)
            ).first()

            if payment_record:
                payment_record.razorpay_order_id = payment.get('id')
                payment_record.payment_method = PaymentMethod.RAZORPAY
                if payment_record.payment_status is None:
                    payment_record.payment_status = PaymentStatus.PENDING
                payment_record.updated_at = datetime.utcnow()
                session.add(payment_record)
            else:
                payment_record = Payment(
                    order_id=order_id,
                    amount=amount,
                    payment_method=PaymentMethod.RAZORPAY,
                    payment_status=PaymentStatus.PENDING,
                    razorpay_order_id=payment.get('id')
                )
                session.add(payment_record)

            session.commit()

        return payment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def payment_webhook(request: Request, x_razorpay_signature: str = Header(None), session: Session = Depends(get_session)):
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    body = await request.body()
    try:
        client.utility.verify_webhook_signature(
            body.decode(), 
            x_razorpay_signature, 
            settings.RAZORPAY_WEBHOOK_SECRET
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = json.loads(body)
    
    # Handle payment.captured or order.paid
    if event['event'] == 'payment.captured':
        payment_entity = event['payload']['payment']['entity']
        print(f"Payment captured: {payment_entity['id']}")

        # Get order ID from notes (preferred)
        notes = payment_entity.get('notes', {})
        internal_order_id = notes.get('internal_order_id')

        order = None
        payment_record = None

        if internal_order_id:
            order = session.get(Order, int(internal_order_id))
            if order:
                payment_record = session.exec(
                    select(Payment).where(Payment.order_id == order.id)
                ).first()
        else:
            # Fallback: resolve order using razorpay order id
            razorpay_order_id = payment_entity.get('order_id')
            if razorpay_order_id:
                payment_record = session.exec(
                    select(Payment).where(Payment.razorpay_order_id == razorpay_order_id)
                ).first()
                if payment_record:
                    order = session.get(Order, payment_record.order_id)

        if order:
            # Update order status
            order.payment_status = OrderPaymentStatus.PAID
            session.add(order)

            # Update or create payment record
            if payment_record:
                payment_record.payment_id = payment_entity['id']
                payment_record.razorpay_order_id = payment_entity.get('order_id')
                payment_record.razorpay_signature = payment_entity.get('signature')
                payment_record.payment_status = PaymentStatus.SUCCESS
                payment_record.updated_at = datetime.utcnow()
                session.add(payment_record)
            else:
                payment_record = Payment(
                    order_id=order.id,
                    payment_id=payment_entity['id'],
                    razorpay_order_id=payment_entity.get('order_id'),
                    razorpay_signature=payment_entity.get('signature'),
                    amount=order.final_amount,
                    payment_method=PaymentMethod.RAZORPAY,
                    payment_status=PaymentStatus.SUCCESS
                )
                session.add(payment_record)

            session.commit()

            # Send order confirmation email after successful payment
            try:
                user = session.get(User, order.user_id)
                if user:
                    from app.models.order import OrderItem
                    from app.models.product import Product
                    from sqlmodel import select

                    order_items = session.exec(
                        select(OrderItem).where(OrderItem.order_id == order.id)
                    ).all()

                    product_details = []
                    order_items_for_email = []
                    for item in order_items:
                        product = session.get(Product, item.product_id)
                        if product:
                            product_details.append({
                                'id': product.id,
                                'name': product.name,
                                'selling_price': getattr(product, 'selling_price', None) or product.mrp,
                                'mrp': product.mrp
                            })
                            order_items_for_email.append({
                                'product_id': item.product_id,
                                'quantity': item.quantity
                            })

                    shipping_email = order.shipping_address.get('email')
                    if not shipping_email:
                        print(f"Warning: No email found in shipping address for order {order.id}")
                        return {"status": "ok"}

                    shipping_addr = order.shipping_address
                    delivery_address_str = f"{shipping_addr.get('full_name', '')}, {shipping_addr.get('address', '')}, {shipping_addr.get('city', '')}, {shipping_addr.get('state', '')} - {shipping_addr.get('pincode', '')}"

                    order_date = order.created_at.strftime("%B %d, %Y at %I:%M %p")
                    send_order_success_email(
                        to_email=shipping_email,
                        user_name=user.name or "Valued Customer",
                        order_id=order.id,
                        order_date=order_date,
                        order_items=order_items_for_email,
                        product_details=product_details,
                        subtotal=order.total_amount or 0.0,
                        shipping=0.0,
                        total_amount=order.total_amount or 0.0,
                        delivery_address=delivery_address_str,
                        payment_method="online"
                    )
                    print(f"Order confirmation email sent for order {order.id} to {shipping_email}")
                else:
                    print(f"Warning: User not found for order {order.id}")
            except Exception as e:
                print(f"Failed to send order confirmation email for order {order.id}: {e}")

    return {"status": "ok"}
