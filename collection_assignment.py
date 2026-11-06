from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import AssignmentStatus


class CollectionAssignmentCreate(BaseModel):
    pickup_id: UUID
    driver_id: UUID
    vehicle_id: UUID
    field_worker_ids: list[UUID] = Field(default_factory=list)

    scheduled_date: date
    scheduled_time_slot: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("scheduled_date")
    @classmethod
    def validate_scheduled_date(cls, value: date) -> date:
        if value < date.today():
            raise ValueError("Scheduled date cannot be in the past")
        return value

    @field_validator("field_worker_ids")
    @classmethod
    def validate_field_worker_ids(
        cls,
        value: list[UUID],
    ) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate field worker IDs are not allowed")
        return value

    @field_validator("scheduled_time_slot", "notes")
    @classmethod
    def clean_optional_text(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return value

        value = value.strip()

        if not value:
            return None

        return value


class CollectionAssignmentUpdate(BaseModel):
    driver_id: Optional[UUID] = None
    vehicle_id: Optional[UUID] = None
    field_worker_ids: Optional[list[UUID]] = None

    scheduled_date: Optional[date] = None

    scheduled_time_slot: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("scheduled_date")
    @classmethod
    def validate_scheduled_date(
        cls,
        value: Optional[date],
    ) -> Optional[date]:
        if value is not None and value < date.today():
            raise ValueError("Scheduled date cannot be in the past")
        return value

    @field_validator("field_worker_ids")
    @classmethod
    def validate_field_worker_ids(
        cls,
        value: Optional[list[UUID]],
    ) -> Optional[list[UUID]]:
        if value is None:
            return value

        if len(value) != len(set(value)):
            raise ValueError("Duplicate field worker IDs are not allowed")

        return value

    @field_validator("scheduled_time_slot", "notes")
    @classmethod
    def clean_optional_text(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return value

        value = value.strip()

        if not value:
            return None

        return value


class CollectionAssignmentStatusUpdate(BaseModel):
    status: AssignmentStatus
    cancellation_reason: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("cancellation_reason")
    @classmethod
    def clean_cancellation_reason(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        if value is None:
            return value

        value = value.strip()

        if not value:
            return None

        return value


class CollectionAssignmentResponse(BaseModel):
    id: UUID
    assignment_code: str

    pickup_id: UUID
    driver_id: UUID
    vehicle_id: UUID
    assigned_by_user_id: Optional[UUID]

    field_worker_ids: list[UUID] = Field(default_factory=list)

    scheduled_date: date
    scheduled_time_slot: Optional[str]

    status: AssignmentStatus
    notes: Optional[str]
    cancellation_reason: Optional[str]

    assigned_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)