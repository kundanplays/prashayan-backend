from typing import Optional
from sqlmodel import Session
from app.models.history import LoginHistory, SearchHistory

class HistoryService:
    def __init__(self, session: Session):
        self.session = session

    def log_login(self, user_id: int, ip_address: Optional[str], user_agent: Optional[str]):
        entry = LoginHistory(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.session.add(entry)
        self.session.commit()

    def log_search(self, query: str, user_id: Optional[int] = None):
        entry = SearchHistory(
            query=query,
            user_id=user_id
        )
        self.session.add(entry)
        self.session.commit()
