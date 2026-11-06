import hashlib
import re

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from core.constants import UserRole
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    decode_token
)
from models.user import User
from models.password_reset import PasswordResetToken
from repositories.user_repository import UserRepository


class AuthService:

    def __init__(self, db: Session):

        self.db = db
        self.user_repo = UserRepository(db)

    @staticmethod
    def validate_password(password: str):

        if not re.search(r"[A-Z]", password):
            raise HTTPException(
                status_code=422,
                detail="Password must contain an uppercase letter"
            )

        if not re.search(r"[a-z]", password):
            raise HTTPException(
                status_code=422,
                detail="Password must contain a lowercase letter"
            )

        if not re.search(r"\d", password):
            raise HTTPException(
                status_code=422,
                detail="Password must contain a number"
            )

        if not re.search(r"[^A-Za-z0-9]", password):
            raise HTTPException(
                status_code=422,
                detail="Password must contain a special character"
            )

    def register_user(self, data):

        self.validate_password(data.password)

        email = str(data.email).lower().strip()

        existing_user = self.user_repo.get_by_email(email)

        if existing_user:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        user = User(
            full_name=data.full_name.strip(),
            email=email,
            hashed_password=hash_password(data.password),
            phone_number=data.phone_number,
            role=UserRole.CUSTOMER
        )

        try:

            self.user_repo.create(user)
            self.db.commit()
            self.db.refresh(user)

            return user

        except Exception:

            self.db.rollback()
            raise

    def login(self, email: str, password: str):

        user = self.user_repo.get_by_email(
            email.lower().strip()
        )

        if not user or not verify_password(
            password,
            user.hashed_password
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if not user.is_active:

            raise HTTPException(
                status_code=403,
                detail="Your account is inactive"
            )

        if user.deleted_at is not None:

            raise HTTPException(
                status_code=403,
                detail="Your account is unavailable"
            )

        access_token = create_access_token(
            str(user.id),
            user.token_version
        )

        refresh_token = create_refresh_token(
            str(user.id),
            user.token_version
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def refresh_tokens(self, token: str):

        try:

            payload = decode_token(token)

        except Exception:

            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token"
            )

        if payload.get("type") != "refresh":

            raise HTTPException(
                status_code=401,
                detail="Refresh token required"
            )

        user_id = payload.get("sub")

        user = self.user_repo.get_by_id(user_id)

        if not user or user.deleted_at is not None:

            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )

        if not user.is_active:

            raise HTTPException(
                status_code=403,
                detail="Your account is inactive"
            )

        if payload.get("ver") != user.token_version:

            raise HTTPException(
                status_code=401,
                detail="Refresh token has been revoked"
            )

        try:

            user.token_version += 1

            self.db.commit()
            self.db.refresh(user)

            return {
                "access_token": create_access_token(
                    str(user.id),
                    user.token_version
                ),
                "refresh_token": create_refresh_token(
                    str(user.id),
                    user.token_version
                ),
                "token_type": "bearer"
            }

        except Exception:

            self.db.rollback()
            raise

    def logout(self, user: User):

        try:

            user.token_version += 1

            self.db.commit()

            return {
                "message": "Successfully logged out"
            }

        except Exception:

            self.db.rollback()
            raise

    def request_password_reset(self, email: str):

        user = self.user_repo.get_by_email(
            email.lower().strip()
        )

        # Return a generic response to avoid email enumeration.
        if not user or not user.is_active:

            return {
                "message": "If the account exists, password reset instructions will be sent"
            }

        token = create_password_reset_token(
            str(user.id)
        )

        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        try:

            # Invalidate previous unused reset tokens.
            previous_tokens = self.db.scalars(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.is_used.is_(False)
                )
            ).all()

            for old_token in previous_tokens:
                old_token.is_used = True

            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(
                    minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
                )
            )

            self.db.add(reset_record)
            self.db.commit()

            response = {
                "message": "Password reset instructions generated"
            }

            # Local development only. Production will send this
            # through an email provider instead.
            if settings.ENVIRONMENT == "development":
                response["reset_token"] = token

            return response

        except Exception:

            self.db.rollback()
            raise

    def reset_password(self, token: str, new_password: str):

        self.validate_password(new_password)

        try:

            payload = decode_token(token)

        except Exception:

            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset token"
            )

        if payload.get("type") != "password_reset":

            raise HTTPException(
                status_code=400,
                detail="Invalid password reset token"
            )

        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        reset_record = self.db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.is_used.is_(False)
            )
        )

        now = datetime.now(timezone.utc)

        if not reset_record:

            raise HTTPException(
                status_code=400,
                detail="Reset token has already been used or is invalid"
            )

        expires_at = reset_record.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:

            raise HTTPException(
                status_code=400,
                detail="Password reset token has expired"
            )

        user = self.user_repo.get_by_id(
            reset_record.user_id
        )

        if not user or not user.is_active:

            raise HTTPException(
                status_code=400,
                detail="User account is unavailable"
            )

        try:

            user.hashed_password = hash_password(new_password)

            user.token_version += 1

            reset_record.is_used = True

            self.db.commit()

            return {
                "message": "Password reset successfully"
            }

        except Exception:

            self.db.rollback()
            raise

    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ):

        self.validate_password(new_password)

        if not verify_password(
            current_password,
            user.hashed_password
        ):

            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect"
            )

        if current_password == new_password:

            raise HTTPException(
                status_code=422,
                detail="New password must be different"
            )

        try:

            user.hashed_password = hash_password(new_password)

            user.token_version += 1

            self.db.commit()

            return {
                "message": "Password changed successfully"
            }

        except Exception:

            self.db.rollback()
            raise