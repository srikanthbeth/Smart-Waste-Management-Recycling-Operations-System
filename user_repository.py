from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str):

        statement = select(User).where(
            User.email == email.lower(),
            User.deleted_at.is_(None)
        )

        return self.db.scalar(statement)

    def get_by_id(self, user_id):

        if isinstance(user_id, str):
            user_id = UUID(user_id)

        return self.db.get(User, user_id)

    def create(self, user: User):

        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)

        return user

    def update(self, user: User):

        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)

        return user