import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_email(to_email: str, subject: str, body: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.MAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(settings.MAIL_FROM, to_email, text)
        server.quit()
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_order_confirmation(to_email: str, order_id: int, amount: float):
    subject = f"Prashayan Order Configuration #{order_id}"
    body = f"""
    <h1>Thank you for your order!</h1>
    <p>Your order <b>#{order_id}</b> has been successfully placed.</p>
    <p>Total Amount: <b>₹{amount}</b></p>
    <p>We will notify you once it ships.</p>
    <br>
    <p>Best,<br>Team Prashayan</p>
    """
    send_email(to_email, subject, body)

def send_status_update(to_email: str, order_id: int, status: str, tracking: str = None):
    subject = f"Order Update: #{order_id} is {status}"
    body = f"""
    <h1>Order Update</h1>
    <p>Your order <b>#{order_id}</b> is now <b>{status}</b>.</p>
    {f'<p>Tracking ID: {tracking}</p>' if tracking else ''}
    <br>
    <p>Best,<br>Team Prashayan</p>
    """
    send_email(to_email, subject, body)
