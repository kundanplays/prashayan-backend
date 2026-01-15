from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.user import UserService
from pydantic import BaseModel

router = APIRouter()

class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(session)

@router.get("/", response_model=List[User])
def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
):
    """
    Retrieve users. Only for superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    users = service.get_all_users()
    return users[skip : skip + limit]

@router.get("/me", response_model=User)
def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Get current user.
    """
    return current_user

@router.patch("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
):
    """
    Update a user. Only for superusers.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    updated_user = service.update_user_status(user_id, user_in.is_active, user_in.is_superuser)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user
