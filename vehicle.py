from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import VehicleType, FuelType, VehicleStatus


class VehicleCreate(BaseModel):
    vehicle_code: str = Field(min_length=2, max_length=30)
    registration_number: str = Field(min_length=3, max_length=30)
    vehicle_type: VehicleType
    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    manufacturing_year: int = Field(
        ge=1980,
        le=date.today().year + 1,
    )
    fuel_type: FuelType
    capacity_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    current_odometer_km: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    location_id: UUID | None = None
    notes: str | None = None

    @field_validator("vehicle_code", "registration_number", mode="before")
    @classmethod
    def normalize_codes(cls, value):
        if isinstance(value, str):
            return value.strip().upper().replace(" ", "")
        return value

    @field_validator("make", "model", mode="before")
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("This field cannot be empty")
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def clean_notes(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class VehicleUpdate(BaseModel):
    vehicle_code: str | None = Field(
        default=None, min_length=2, max_length=30
    )
    registration_number: str | None = Field(
        default=None, min_length=3, max_length=30
    )
    vehicle_type: VehicleType | None = None
    make: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    manufacturing_year: int | None = Field(
        default=None,
        ge=1980,
        le=date.today().year + 1,
    )
    fuel_type: FuelType | None = None
    capacity_kg: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2
    )
    current_odometer_km: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    location_id: UUID | None = None
    notes: str | None = None

    @field_validator("vehicle_code", "registration_number", mode="before")
    @classmethod
    def normalize_codes(cls, value):
        if isinstance(value, str):
            return value.strip().upper().replace(" ", "")
        return value

    @field_validator("make", "model", mode="before")
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("This field cannot be empty")
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def clean_notes(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class VehicleStatusUpdate(BaseModel):
    status: VehicleStatus


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vehicle_code: str
    registration_number: str
    vehicle_type: VehicleType
    make: str
    model: str
    manufacturing_year: int
    fuel_type: FuelType
    capacity_kg: Decimal
    current_odometer_km: Decimal
    location_id: UUID | None
    status: VehicleStatus
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime