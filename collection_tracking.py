
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.constants import CollectionTrackingStatus


class CollectionTrackingCreate(BaseModel):
    assignment_id: UUID

    remarks: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    photo_urls: list[str] = Field(
        default_factory=list,
        max_length=10,
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value

    @field_validator("photo_urls")
    @classmethod
    def validate_photo_urls(cls, values):
        cleaned = []

        for url in values:
            url = url.strip()

            if not url.startswith(("http://", "https://")):
                raise ValueError(
                    "Photo URLs must start with http:// or https://"
                )

            cleaned.append(url)

        return cleaned


class CollectionTrackingUpdate(BaseModel):
    collected_quantity_kg: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )

    remarks: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    photo_urls: Optional[list[str]] = Field(
        default=None,
        max_length=10,
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value

    @field_validator("photo_urls")
    @classmethod
    def validate_photo_urls(cls, values):
        if values is None:
            return values

        cleaned = []

        for url in values:
            url = url.strip()

            if not url.startswith(("http://", "https://")):
                raise ValueError(
                    "Photo URLs must start with http:// or https://"
                )

            cleaned.append(url)

        return cleaned


class CollectionTrackingStatusUpdate(BaseModel):
    status: CollectionTrackingStatus

    collected_quantity_kg: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )

    remarks: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def validate_status_details(self):
        if self.status in (
            CollectionTrackingStatus.PARTIALLY_COMPLETED,
            CollectionTrackingStatus.FAILED,
        ):
            if not self.remarks:
                raise ValueError(
                    "Remarks are required for partially completed or failed collections"
                )

        if self.status in (
            CollectionTrackingStatus.COMPLETED,
            CollectionTrackingStatus.PARTIALLY_COMPLETED,
        ):
            if self.collected_quantity_kg is None:
                raise ValueError(
                    "Collected quantity is required for completed collections"
                )

        return self


class CollectionTrackingResponse(BaseModel):
    id: UUID
    tracking_code: str

    assignment_id: UUID
    pickup_id: UUID
    tracked_by_user_id: UUID

    status: CollectionTrackingStatus

    collected_quantity_kg: Optional[Decimal]

    started_at: datetime
    completed_at: Optional[datetime]

    remarks: Optional[str]
    photo_urls: list[str]

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
