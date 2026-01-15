import razorpay
import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from app.core.config import settings
from app.db.session import get_session
from sqlmodel import Session
from app.models.order import Order
from app.services.email import send_order_confirmation, send_status_update
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
                
                # Fetch user email to send confirmation
                user = session.get(User, order.user_id)
                if user:
                    send_order_confirmation(user.email, order.id, order.total_amount)

    return {"status": "ok"}
