import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field
)

from core.constants import UserRole


class UserRegister(BaseModel):

    full_name: str = Field(
        min_length=2,
        max_length=150
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )

    phone_number: str | None = Field(
        default=None,
        max_length=20
    )


class UserResponse(BaseModel):

    id: uuid.UUID

    full_name: str

    email: EmailStr

    phone_number: str | None

    role: UserRole

    is_active: bool

    is_verified: bool

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class UserActivationUpdate(BaseModel):

    is_active: bool