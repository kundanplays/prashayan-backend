import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from typing import List, Optional
from app.core.config import settings

def send_email(to_email: str, subject: str, body: str, embed_logo: bool = True):
    try:
        msg = MIMEMultipart('related')
        msg['From'] = settings.MAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        # Embed logo if requested
        if embed_logo:
            try:
                with open('email_templates/logo.png', 'rb') as f:
                    logo = MIMEImage(f.read())
                    logo.add_header('Content-ID', '<logo>')
                    logo.add_header('Content-Disposition', 'inline')
                    msg.attach(logo)
            except FileNotFoundError:
                print("Warning: logo.png not found, sending email without logo")

        if settings.MAIL_SSL:
            print(f"Connecting to {settings.MAIL_SERVER}:{settings.MAIL_PORT} via SSL...")
            server = smtplib.SMTP_SSL(settings.MAIL_SERVER, settings.MAIL_PORT)
        else:
            print(f"Connecting to {settings.MAIL_SERVER}:{settings.MAIL_PORT} via TLS...")
            server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
            server.starttls()

        print(f"Logging in as {settings.MAIL_USERNAME}...")
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(settings.MAIL_FROM, to_email, text)
        server.quit()
        print(f"Email successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def format_order_items_for_email(order_items: List[dict], product_details: List[dict]) -> str:
    """Format order items for email template"""
    items_html = ""
    for item in order_items:
        product_id = item.get('product_id')
        quantity = item.get('quantity')

        # Find product details
        product = next((p for p in product_details if p.get('id') == product_id), None)
        if not product:
            continue

        name = product.get('name', 'Unknown Product')
        price = product.get('selling_price', product.get('mrp', 0))
        item_total = price * quantity

        items_html += f"""
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 16px;">
            <tr>
                <td style="width: 70%; padding: 8px 0;">
                    <p style="margin: 0 0 4px; font-size: 15px; font-weight: 600; color: #2E5C55;">{name}</p>
                    <p style="margin: 0; font-size: 13px; color: #8A9A95;">Quantity: {quantity}</p>
                </td>
                <td style="width: 30%; text-align: right; padding: 8px 0;">
                    <p style="margin: 0; font-size: 15px; font-weight: 600; color: #2E5C55;">₹{item_total:.2f}</p>
                </td>
            </tr>
        </table>"""

    return items_html

def format_address_for_email(address_data: dict) -> str:
    """Format shipping address for email"""
    full_name = address_data.get('full_name', '')
    email = address_data.get('email', '')
    phone = address_data.get('phone', '')
    address = address_data.get('address', '')
    city = address_data.get('city', '')
    state = address_data.get('state', '')
    pincode = address_data.get('pincode', '')

    return f"{full_name}<br>{address}<br>{city}, {state} {pincode}<br>{phone}<br>{email}"

def send_order_success_email(
    to_email: str,
    user_name: str,
    order_id: int,
    order_date: str,
    order_items: List[dict],
    product_details: List[dict],
    subtotal: float,
    shipping: float,
    discount: float = 0,
    discount_code: str = "",
    total_amount: float = 0,
    delivery_address: str = "",
    payment_method: str = "cod"
):
    """Send order success email using HTML template"""
    try:
        with open('email_templates/order_success_email.html', 'r', encoding='utf-8') as f:
            template = f.read()

        # Format order items
        order_items_html = format_order_items_for_email(order_items, product_details)

        # Replace placeholders
        replacements = {
            '{{user_name}}': user_name,
            '{{order_id}}': str(order_id),
            '{{order_date}}': order_date,
            '{{order_items}}': order_items_html,
            '{{subtotal}}': f"{subtotal:.2f}",
            '{{shipping}}': f"{shipping:.2f}",
            '{{total_amount}}': f"{total_amount:.2f}",
            '{{delivery_address}}': delivery_address,
            '{{tracking_url}}': f"http://localhost:3000/track-order/{order_id}"  # Adjust URL as needed
        }

        # Handle discount conditionally
        if discount > 0 and discount_code:
            replacements['{{discount}}'] = f"{discount:.2f}"
            replacements['{{discount_code}}'] = discount_code
            # Replace the conditional discount section
            discount_section = f"""
            <tr>
                <td style="padding: 4px 0; font-size: 14px; color: #AA8C2C;">Discount ({discount_code})</td>
                <td style="padding: 4px 0; text-align: right; font-size: 14px; color: #AA8C2C;">-₹{discount:.2f}</td>
            </tr>"""
            template = template.replace('{{#if discount}}', '').replace('{{/if}}', '')
            template = template.replace('<!-- Discount row will be inserted here -->', discount_section)
        else:
            # Remove discount section if no discount
            import re
            template = re.sub(r'{{#if discount}}.*?{{/if}}', '', template, flags=re.DOTALL)

        # Apply replacements
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)

        subject = f"Order Confirmed - Prashayan #{order_id}"
        send_email(to_email, subject, template)

    except Exception as e:
        print(f"Failed to send order success email: {e}")

def send_delivery_feedback_email(
    to_email: str,
    user_name: str,
    order_id: int,
    delivery_date: str,
    order_items_summary: str,
    feedback_url: str
):
    """Send delivery feedback email using HTML template"""
    try:
        with open('email_templates/order_delivery_feedback_email.html', 'r', encoding='utf-8') as f:
            template = f.read()

        replacements = {
            '{{user_name}}': user_name,
            '{{order_id}}': str(order_id),
            '{{delivery_date}}': delivery_date,
            '{{order_items_summary}}': order_items_summary,
            '{{feedback_url}}': feedback_url
        }

        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)

        subject = f"Your Order #{order_id} Has Been Delivered - Prashayan"
        send_email(to_email, subject, template)

    except Exception as e:
        print(f"Failed to send delivery feedback email: {e}")

def send_order_cancellation_email(
    to_email: str,
    user_name: str,
    order_id: int,
    cancellation_reason: str,
    order_items_summary: str,
    total_amount: float
):
    """Send order cancellation email using HTML template"""
    try:
        with open('email_templates/order_cancellation_email.html', 'r', encoding='utf-8') as f:
            template = f.read()

        replacements = {
            '{{user_name}}': user_name,
            '{{order_id}}': str(order_id),
            '{{cancellation_reason}}': cancellation_reason,
            '{{order_items_summary}}': order_items_summary,
            '{{total_amount}}': f"{total_amount:.2f}"
        }

        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)

        subject = f"Order Cancelled - Prashayan #{order_id}"
        send_email(to_email, subject, template)

    except Exception as e:
        print(f"Failed to send order cancellation email: {e}")

def send_shipping_notification_email(
    to_email: str,
    user_name: str,
    order_id: int,
    tracking_id: str = None,
    estimated_delivery: str = None
):
    """Send shipping notification email"""
    subject = f"Your Order #{order_id} Has Been Shipped - Prashayan"

    tracking_info = ""
    if tracking_id:
        tracking_info = f"<p><strong>Tracking ID:</strong> {tracking_id}</p>"
    if estimated_delivery:
        tracking_info += f"<p><strong>Estimated Delivery:</strong> {estimated_delivery}</p>"

    body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Order Shipped</title>
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #2E5C55 0%, #3E7A70 100%); color: white; padding: 20px; text-align: center;">
            <h1>🚚 Your Order Has Been Shipped!</h1>
        </div>
        <div style="padding: 20px;">
            <h2>Hello {user_name},</h2>
            <p>Great news! Your order <strong>#{order_id}</strong> has been shipped and is on its way to you.</p>
            {tracking_info}
            <p>You can track your order status anytime from your account dashboard.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="http://localhost:3000/track-order/{order_id}"
                   style="background-color: #D4AF37; color: #2E5C55; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Track Your Order
                </a>
            </div>
            <p>Thank you for choosing Prashayan!</p>
            <p>Best regards,<br>Team Prashayan</p>
        </div>
    </body>
    </html>
    """
    send_email(to_email, subject, body)
