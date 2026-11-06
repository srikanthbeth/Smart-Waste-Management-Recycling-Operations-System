
from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.constants import LocationType, LocationStatus


class LocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)
    description: str | None = None

    location_type: LocationType
    parent_id: UUID | None = None

    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("name", "code")
    @classmethod
    def normalize_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must be provided together"
            )
        return self


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    location_type: LocationType | None = None
    parent_id: UUID | None = None

    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must be provided together"
            )
        return self


class LocationStatusUpdate(BaseModel):
    status: LocationStatus


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: str | None
    location_type: LocationType
    parent_id: UUID | None

    address: str | None
    city: str | None
    state: str | None
    postal_code: str | None

    latitude: float | None
    longitude: float | None

    status: LocationStatus
    is_active: bool

    created_at: datetime
    updated_at: datetime
