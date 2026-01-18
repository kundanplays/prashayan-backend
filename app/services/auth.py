from datetime import datetime, timedelta
import random
import string
from typing import Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.models.user import User
from app.core.config import settings
from app.services.email import send_email

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            # Use the default from config (7 days)
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    def get_user_by_email(self, email: str) -> Optional[User]:
        # Use ilike for case-insensitive lookup
        return self.session.exec(select(User).where(User.email == email)).first() or \
               self.session.exec(select(User).where(User.email.ilike(email))).first()

    def register_user(self, email: str, password: str, name: str = None, phone: str = None) -> User:
        user = self.get_user_by_email(email)

        if user and user.is_verified:
            raise HTTPException(status_code=400, detail="Email already registered")

        if user:
            # Update existing temporary user (from OTP generation)
            user.name = name
            user.password_hash = self.get_password_hash(password)
            user.phone = phone
            user.is_verified = True
            user.otp_code = None  # Clear OTP after successful registration
            user.otp_expires_at = None
        else:
            # Create new user (fallback, shouldn't happen in normal flow)
            user = User(
                email=email,
                name=name,
                password_hash=self.get_password_hash(password),
                phone=phone,
                is_active=True,
                is_verified=True
            )

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def authenticate_user(self, email: str, password: str) -> tuple[Optional[User], Optional[str]]:
        user = self.get_user_by_email(email)
        if not user:
            return None, "User not found. Please check your email or register a new account."
        if not self.verify_password(password, user.password_hash):
            return None, "Incorrect password. Please try again."
        return user, None

    def generate_otp_for_email(self, email: str) -> str:
        """Generate OTP for email (creates temporary user if needed)"""
        user = self.get_user_by_email(email)

        # If user exists and is already verified (fully registered), prevent re-registration
        if user and user.is_verified and user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please sign in instead."
            )

        # If user doesn't exist, create a temporary unverified user
        if not user:
            user = User(
                email=email,
                password_hash="",  # Temporary, will be set during registration
                is_active=True,
                is_verified=False,
                is_guest=False
            )
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

        # Generate OTP
        otp = "".join(random.choices(string.digits, k=6))
        user.otp_code = otp
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        self.session.add(user)
        self.session.commit()

        # Send OTP via Email using template
        self.send_otp_email(user.email, user.name or "Valued Customer", otp)
        return otp

    def send_otp_email(self, email: str, user_name: str, otp_code: str):
        """Send OTP email using HTML template"""
        try:
            # Read the template
            template_path = "email_templates/otp_email.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()

            # Replace placeholders
            html_content = html_template.replace('{{user_name}}', user_name)
            html_content = html_content.replace('{{otp_code}}', otp_code)

            # Send the email
            send_email(email, "Verify Your Email - Prashayan", html_content)
        except Exception as e:
            print(f"Failed to send OTP email template: {e}")
            # Fallback to simple email
            send_email(email, "Your Verification OTP", f"Your OTP is: <b>{otp_code}</b>. It expires in 10 minutes.")

    def verify_otp(self, email: str, otp: str) -> bool:
        user = self.get_user_by_email(email)
        if not user or not user.otp_code:
            return False

        if user.otp_code != otp:
            return False

        if datetime.utcnow() > user.otp_expires_at:
            return False

        # Verify success - mark as verified but don't clear OTP yet
        # OTP will be cleared during registration
        user.is_verified = True
        self.session.add(user)
        self.session.commit()
        return True

    def create_password_reset_token(self, email: str) -> Optional[str]:
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        # Generate a secure random token
        token = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        user.reset_token = token
        # Token valid for 1 hour? For now just storing token. 
        # Ideally add reset_token_expires_at
        
        self.session.add(user)
        self.session.commit()
        
        # In a real app, send this link via email:
        # link = f"https://prashayan.com/auth/reset-password?token={token}"
        send_email(user.email, "Password Reset Request", f"Use this token to reset your password: <b>{token}</b>")
        return token

    def reset_password(self, token: str, new_password: str) -> bool:
        user = self.session.exec(select(User).where(User.reset_token == token)).first()
        if not user:
            return False
            
        user.password_hash = self.get_password_hash(new_password)
        user.reset_token = None
        self.session.add(user)
        self.session.commit()
        return True
