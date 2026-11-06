
from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from core.constants import WasteCategoryStatus


class WasteCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)
    description: str | None = None
    is_recyclable: bool = False
    is_hazardous: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = " ".join(value.strip().split())

        if not value:
            raise ValueError("Category name cannot be empty")

        return value

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper().replace(" ", "_")

        if not value:
            raise ValueError("Category code cannot be empty")

        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None

        return value


class WasteCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    code: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = None
    is_recyclable: bool | None = None
    is_hazardous: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = " ".join(value.strip().split())

            if not value:
                raise ValueError("Category name cannot be empty")

        return value

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip().upper().replace(" ", "_")

            if not value:
                raise ValueError("Category code cannot be empty")

        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None

        return value


class WasteCategoryStatusUpdate(BaseModel):
    status: WasteCategoryStatus


class WasteCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: str | None
    is_recyclable: bool
    is_hazardous: bool
    status: WasteCategoryStatus
    created_at: datetime
    updated_at: datetime
