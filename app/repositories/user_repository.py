import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User

class UserRepository:
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email_normalized == email.lower()).first()

    def get_by_id(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def create(self, db: Session, user: User) -> User:
        db.add(user)
        return user

    def update(self, db: Session, user: User) -> User:
        db.add(user)
        return user
