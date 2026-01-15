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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.session.exec(select(User).where(User.email == email)).first()

    def register_user(self, email: str, password: str, phone: str = None) -> User:
        if self.get_user_by_email(email):
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = User(
            email=email,
            password_hash=self.get_password_hash(password),
            phone=phone,
            is_active=True,
            is_verified=False 
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user

    def generate_otp(self, user: User):
        otp = "".join(random.choices(string.digits, k=6))
        user.otp_code = otp
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        self.session.add(user)
        self.session.commit()
        
        # Send OTP via Email
        send_email(user.email, "Your Verification OTP", f"Your OTP is: <b>{otp}</b>. It expires in 10 minutes.")
        return otp

    def verify_otp(self, email: str, otp: str) -> bool:
        user = self.get_user_by_email(email)
        if not user or not user.otp_code:
            return False
            
        if user.otp_code != otp:
            return False
            
        if datetime.utcnow() > user.otp_expires_at:
            return False
            
        # Verify success
        user.is_verified = True
        user.otp_code = None
        user.otp_expires_at = None
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
