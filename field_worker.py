
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import StaffStatus, StaffAvailability


class FieldWorkerCreate(BaseModel):
    user_id: UUID
    worker_code: str = Field(min_length=3, max_length=30)
    phone: str = Field(min_length=7, max_length=20)
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    joining_date: date = Field(default_factory=date.today)
    notes: str | None = None

    @field_validator("worker_code")
    @classmethod
    def normalize_worker_code(cls, value: str) -> str:
        return value.strip().upper().replace(" ", "")

    @field_validator("phone", "emergency_contact_phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("address", "notes", "emergency_contact_name")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("joining_date")
    @classmethod
    def validate_joining_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Joining date cannot be in the future")
        return value


class FieldWorkerUpdate(BaseModel):
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    joining_date: date | None = None
    notes: str | None = None

    @field_validator("phone", "emergency_contact_phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("address", "notes", "emergency_contact_name")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("joining_date")
    @classmethod
    def validate_joining_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Joining date cannot be in the future")
        return value


class FieldWorkerStatusUpdate(BaseModel):
    status: StaffStatus
    availability: StaffAvailability | None = None


class FieldWorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    worker_code: str
    phone: str
    address: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    joining_date: date
    status: StaffStatus
    availability: StaffAvailability
    notes: str | None
