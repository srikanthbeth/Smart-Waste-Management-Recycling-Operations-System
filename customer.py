
from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.constants import (
    CustomerStatus,
    CustomerType,
    PropertyType,
)


class CustomerCreate(BaseModel):
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    organization_name: str | None = Field(
        default=None,
        max_length=200,
    )
    property_type: PropertyType = PropertyType.HOUSE

    service_address: str = Field(
        min_length=5,
        max_length=2000,
    )
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)

    location_id: UUID | None = None

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    monthly_waste_estimate_kg: float | None = Field(
        default=None,
        gt=0,
        le=1000000,
    )

    notes: str | None = None

    @field_validator(
        "service_address",
        "city",
        "state",
        "postal_code",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = " ".join(value.strip().split())

        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("organization_name")
    @classmethod
    def normalize_organization_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = " ".join(value.strip().split())
            return value or None

        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None

        return value

    @model_validator(mode="after")
    def validate_organization(self):
        organization_types = {
            CustomerType.COMMERCIAL,
            CustomerType.INDUSTRIAL,
            CustomerType.INSTITUTIONAL,
        }

        if (
            self.customer_type in organization_types
            and not self.organization_name
        ):
            raise ValueError(
                "Organization name is required for "
                "commercial, industrial, and institutional customers"
            )

        if (
            self.customer_type == CustomerType.RESIDENTIAL
            and self.organization_name
        ):
            raise ValueError(
                "Residential customers cannot provide an organization name"
            )

        return self


class CustomerUpdate(BaseModel):
    customer_type: CustomerType | None = None

    organization_name: str | None = Field(
        default=None,
        max_length=200,
    )

    property_type: PropertyType | None = None

    service_address: str | None = Field(
        default=None,
        min_length=5,
        max_length=2000,
    )

    city: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    state: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    postal_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=20,
    )

    location_id: UUID | None = None

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    monthly_waste_estimate_kg: float | None = Field(
        default=None,
        gt=0,
        le=1000000,
    )

    notes: str | None = None

    @field_validator(
        "service_address",
        "city",
        "state",
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

    @field_validator("organization_name")
    @classmethod
    def normalize_organization_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = " ".join(value.strip().split())
            return value or None

        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None

        return value


class CustomerStatusUpdate(BaseModel):
    status: CustomerStatus


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    customer_code: str

    customer_type: CustomerType
    organization_name: str | None
    property_type: PropertyType

    service_address: str
    city: str
    state: str
    postal_code: str

    location_id: UUID | None

    latitude: float | None
    longitude: float | None

    monthly_waste_estimate_kg: float | None
    notes: str | None

    status: CustomerStatus

    created_at: datetime
    updated_at: datetime
