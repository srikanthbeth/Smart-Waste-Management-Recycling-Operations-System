
from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from core.constants import PickupPriority, PickupStatus


class PickupCreate(BaseModel):
    waste_category_id: UUID
    location_id: UUID | None = None

    estimated_quantity_kg: float = Field(
        gt=0,
        le=1000000,
    )

    preferred_date: date

    preferred_time_slot: str | None = Field(
        default=None,
        max_length=50,
    )

    pickup_address: str = Field(
        min_length=5,
        max_length=2000,
    )

    city: str = Field(
        min_length=2,
        max_length=100,
    )

    postal_code: str = Field(
        min_length=3,
        max_length=20,
    )

    special_instructions: str | None = None

    @field_validator("preferred_date")
    @classmethod
    def validate_preferred_date(cls, value: date) -> date:
        if value <= date.today():
            raise ValueError("Preferred pickup date must be in the future")

        return value

    @field_validator(
        "pickup_address",
        "city",
        "postal_code",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = " ".join(value.strip().split())

        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("preferred_time_slot")
    @classmethod
    def normalize_time_slot(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = " ".join(value.strip().split())
            return value or None

        return value

    @field_validator("special_instructions")
    @classmethod
    def normalize_instructions(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None

        return value


class PickupUpdate(BaseModel):
    waste_category_id: UUID | None = None
    location_id: UUID | None = None

    estimated_quantity_kg: float | None = Field(
        default=None,
        gt=0,
        le=1000000,
    )

    preferred_date: date | None = None

    preferred_time_slot: str | None = Field(
        default=None,
        max_length=50,
    )

    pickup_address: str | None = Field(
        default=None,
        min_length=5,
        max_length=2000,
    )

    city: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    postal_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=20,
    )

    special_instructions: str | None = None

    @field_validator("preferred_date")
    @classmethod
    def validate_preferred_date(
        cls,
        value: date | None,
    ) -> date | None:
        if value is not None and value <= date.today():
            raise ValueError("Preferred pickup date must be in the future")

        return value

    @field_validator(
        "pickup_address",
        "city",
        "postal_code",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = " ".join(value.strip().split())

            if not value:
                raise ValueError("This field cannot be empty")

        return value

    @field_validator("preferred_time_slot")
    @classmethod
    def normalize_time_slot(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = " ".join(value.strip().split())
            return value or None

        return value

    @field_validator("special_instructions")
    @classmethod
    def normalize_instructions(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None

        return value


class PickupStatusUpdate(BaseModel):
    status: PickupStatus

    rejection_reason: str | None = Field(
        default=None,
        max_length=2000,
    )

    cancellation_reason: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator(
        "rejection_reason",
        "cancellation_reason",
    )
    @classmethod
    def normalize_reason(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None

        return value


class PickupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pickup_code: str

    customer_id: UUID
    waste_category_id: UUID
    location_id: UUID | None

    estimated_quantity_kg: float

    preferred_date: date
    preferred_time_slot: str | None

    pickup_address: str
    city: str
    postal_code: str

    special_instructions: str | None

    priority: PickupPriority
    status: PickupStatus

    rejection_reason: str | None
    cancellation_reason: str | None

    requested_at: datetime
    updated_at: datetime
    completed_at: datetime | None
