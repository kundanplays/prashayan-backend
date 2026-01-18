from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.user import User
from app.core.security import verify_password, get_password_hash, create_access_token
from jose import JWTError, jwt
from app.core.config import settings
from pydantic import BaseModel
from app.services.auth import AuthService

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token", auto_error=False)


class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    phone: Optional[str] = None

class OTPVerify(BaseModel):
    email: str
    code: str

class OTPGenerate(BaseModel):
    email: str

def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session)

@router.post("/register", response_model=User)
def register(user_in: UserCreate, service: AuthService = Depends(get_auth_service)):
    return service.register_user(user_in.email, user_in.password, name=user_in.name, phone=user_in.phone)

from fastapi import Request
from app.services.history import HistoryService

def get_history_service(session: Session = Depends(get_session)) -> HistoryService:
    return HistoryService(session)

@router.post("/token", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AuthService = Depends(get_auth_service),
    history_service: HistoryService = Depends(get_history_service),
    session: Session = Depends(get_session)
):
    user, error_message = service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log Login History
    history_service.log_login(
        user_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    # Check if user is admin - if so, never expire token
    from sqlmodel import select
    from app.models.admin_user import AdminUser
    admin_user = session.exec(select(AdminUser).where(AdminUser.user_id == user.id)).first()

    if admin_user and admin_user.is_active:
        # Admin users get tokens that never expire (100 years)
        access_token_expires = service.create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(days=365*100)  # 100 years
        )
    else:
        # Regular users get normal expiration (7 days from config)
        access_token_expires = service.create_access_token(
            data={"sub": user.email}
        )

    return {"access_token": access_token_expires, "token_type": "bearer"}

@router.post("/otp/generate")
def generate_otp(data: OTPGenerate, service: AuthService = Depends(get_auth_service)):
    service.generate_otp_for_email(data.email)
    return {"message": "OTP sent"}

@router.post("/otp/verify")
def verify_otp(data: OTPVerify, service: AuthService = Depends(get_auth_service)):
    is_valid = service.verify_otp(data.email, data.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    return {"message": "User verified successfully"}

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

@router.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, service: AuthService = Depends(get_auth_service)):
    service.create_password_reset_token(data.email)
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a reset instruction has been sent."}

@router.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirm, service: AuthService = Depends(get_auth_service)):
    success = service.reset_password(data.token, data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"message": "Password updated successfully"}

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Lookup user by email (stored in 'sub')
    # Use ilike for robustness
    user = session.exec(select(User).where(User.email == username)).first() or \
           session.exec(select(User).where(User.email.ilike(username))).first()
    
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_optional(token: str = Depends(oauth2_scheme_optional), session: Session = Depends(get_session)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    return session.exec(select(User).where(User.email == username)).first()
