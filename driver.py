
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import StaffStatus, StaffAvailability


class DriverCreate(BaseModel):
    user_id: UUID
    driver_code: str = Field(min_length=3, max_length=30)
    license_number: str = Field(min_length=3, max_length=50)
    license_type: str = Field(min_length=2, max_length=50)
    license_expiry_date: date
    phone: str = Field(min_length=7, max_length=20)
    address: str | None = None
    joining_date: date = Field(default_factory=date.today)
    notes: str | None = None

    @field_validator("driver_code")
    @classmethod
    def normalize_driver_code(cls, value: str) -> str:
        return value.strip().upper().replace(" ", "")

    @field_validator("license_number")
    @classmethod
    def normalize_license_number(cls, value: str) -> str:
        return value.strip().upper().replace(" ", "")

    @field_validator("license_type", "phone")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("address", "notes")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("license_expiry_date")
    @classmethod
    def validate_license_expiry(cls, value: date) -> date:
        if value <= date.today():
            raise ValueError("Driver license must not be expired")
        return value

    @field_validator("joining_date")
    @classmethod
    def validate_joining_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Joining date cannot be in the future")
        return value


class DriverUpdate(BaseModel):
    license_number: str | None = Field(default=None, min_length=3, max_length=50)
    license_type: str | None = Field(default=None, min_length=2, max_length=50)
    license_expiry_date: date | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    address: str | None = None
    joining_date: date | None = None
    notes: str | None = None

    @field_validator("license_number")
    @classmethod
    def normalize_license_number(cls, value: str | None) -> str | None:
        return value.strip().upper().replace(" ", "") if value else value

    @field_validator("license_type", "phone")
    @classmethod
    def clean_required_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("address", "notes")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("license_expiry_date")
    @classmethod
    def validate_license_expiry(cls, value: date | None) -> date | None:
        if value is not None and value <= date.today():
            raise ValueError("Driver license must not be expired")
        return value

    @field_validator("joining_date")
    @classmethod
    def validate_joining_date(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Joining date cannot be in the future")
        return value


class DriverStatusUpdate(BaseModel):
    status: StaffStatus
    availability: StaffAvailability | None = None


class DriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    driver_code: str
    license_number: str
    license_type: str
    license_expiry_date: date
    phone: str
    address: str | None
    joining_date: date
    status: StaffStatus
    availability: StaffAvailability
    notes: str | None
