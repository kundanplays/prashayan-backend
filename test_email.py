import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv("/Users/kundanatspontaa/Desktop/prashayan-backend/.env")

def test_smtp():
    mail_server = os.getenv("Outgoing_Server_Name", "smtppro.zoho.in")
    mail_port = int(os.getenv("PORT", 465))
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("APP_PASSWORD")
    mail_from = os.getenv("MAIL_FROM")
    mail_ssl = os.getenv("MAIL_SSL", "True").lower() == "true"

    print(f"Testing with Server: {mail_server}, Port: {mail_port}, SSL: {mail_ssl}")
    print(f"Username: {mail_username}")

    try:
        msg = MIMEMultipart()
        msg['From'] = mail_from
        msg['To'] = "kundan.singh56@gmail.com"
        msg['Subject'] = "SMTP Test"
        msg.attach(MIMEText("Test body", 'html'))

        if mail_ssl and mail_port == 465:
            print("Using SMTP_SSL...")
            server = smtplib.SMTP_SSL(mail_server, mail_port)
        else:
            print("Using STARTTLS...")
            server = smtplib.SMTP(mail_server, mail_port)
            server.starttls()
            
        server.login(mail_username, mail_password)
        server.sendmail(mail_from, "kundan.singh56@gmail.com", msg.as_string())
        server.quit()
        print("Success! Email sent.")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_smtp()
