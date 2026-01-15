from typing import List, Optional
from sqlmodel import Session, select
from app.models.user import User

class UserService:
    def __init__(self, session: Session):
        self.session = session

    def get_all_users(self) -> List[User]:
        return self.session.exec(select(User)).all()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)

    def update_user_status(self, user_id: int, is_active: bool = None, is_superuser: bool = None) -> Optional[User]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        if is_active is not None:
            user.is_active = is_active
        if is_superuser is not None:
            user.is_superuser = is_superuser
            
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
