from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from core.constants import UserRole
from core.permissions import require_roles

from models.user import User
from schemas.user import UserResponse, UserActivationUpdate
from schemas.auth import MessageResponse

router = APIRouter(
    prefix="/api/v1/users",
    tags=["User Management"]
)


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse
)
def update_user_status(
    user_id: UUID,
    data: UserActivationUpdate,
    current_user: User = Depends(
        require_roles(UserRole.SUPER_ADMIN)
    ),
    db: Session = Depends(get_db)
):

    user = db.get(User, user_id)

    if not user or user.deleted_at is not None:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.id == current_user.id and not data.is_active:

        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account"
        )

    try:

        user.is_active = data.is_active
        user.token_version += 1

        db.commit()
        db.refresh(user)

        return user

    except Exception:

        db.rollback()
        raise


@router.delete(
    "/{user_id}",
    response_model=MessageResponse
)
def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(
        require_roles(UserRole.SUPER_ADMIN)
    ),
    db: Session = Depends(get_db)
):

    user = db.get(User, user_id)

    if not user or user.deleted_at is not None:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    if user.id == current_user.id:

        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account"
        )

    try:

        from datetime import datetime, timezone

        user.is_active = False
        user.deleted_at = datetime.now(timezone.utc)
        user.token_version += 1

        db.commit()

        return {
            "message": "User deactivated successfully"
        }

    except Exception:

        db.rollback()
        raise