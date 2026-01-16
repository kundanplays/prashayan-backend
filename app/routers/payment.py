import razorpay
import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from app.core.config import settings
from app.db.session import get_session
from sqlmodel import Session
from app.models.order import Order
from app.services.email import send_order_success_email, format_address_for_email, format_order_items_for_email
from app.models.user import User

router = APIRouter()

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@router.post("/create-order")
async def create_payment_order(amount: float):
    # Amount needed in paise
    data = {"amount": int(amount * 100), "currency": "INR", "payment_capture": 1}
    try:
        payment = client.order.create(data=data)
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
        # Metadata logic would go here to link back to internal Order ID if passed in notes
        # For this demo, we assume we find the order via notes or similar mechanism 
        print(f"Payment captured: {payment_entity['id']}")
        
        # Example: Link to order and update DB + Send Email
        # This part requires the frontend to pass order_id in notes when creating razorpay order
        notes = payment_entity.get('notes', {})
        internal_order_id = notes.get('internal_order_id')
        
        if internal_order_id:
            order = session.get(Order, int(internal_order_id))
            if order:
                order.status = "paid"
                session.add(order)
                session.commit()
                
                # Fetch user and order details for comprehensive email
                user = session.get(User, order.user_id)
                if user:
                    # Get order items and product details
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

                    # Format delivery address
                    delivery_address = format_address_for_email(order.shipping_address)

                    # Send comprehensive order success email
                    order_date = order.created_at.strftime("%B %d, %Y at %I:%M %p")
                    send_order_success_email(
                        to_email=order.shipping_address.get('email'),
                        user_name=user.name,
                        order_id=order.id,
                        order_date=order_date,
                        order_items=order_items_for_email,
                        product_details=product_details,
                        subtotal=order.total_amount,
                        shipping=0.0,  # You can modify this based on your shipping logic
                        total_amount=order.total_amount,
                        delivery_address=delivery_address,
                        payment_method="online"  # Since this is from payment webhook
                    )

    return {"status": "ok"}
