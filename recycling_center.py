
from uuid import UUID
from pydantic import computed_field


from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.constants import RecyclingCenterStatus


class RecyclingCenterCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)
    description: str | None = None

    location_id: UUID
    manager_user_id: UUID | None = None

    processing_capacity_kg_per_day: float = Field(gt=0)

    is_available: bool = True

    accepted_waste_category_ids: list[UUID] = Field(
        default_factory=list
    )

    @field_validator("name", "code")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("accepted_waste_category_ids")
    @classmethod
    def validate_category_ids(
        cls,
        value: list[UUID],
    ) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate waste category IDs are not allowed")

        return value


class RecyclingCenterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    code: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = None

    location_id: UUID | None = None
    manager_user_id: UUID | None = None

    processing_capacity_kg_per_day: float | None = Field(
        default=None,
        gt=0,
    )

    is_available: bool | None = None

    accepted_waste_category_ids: list[UUID] | None = None

    @field_validator("name", "code")
    @classmethod
    def validate_optional_text_fields(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("accepted_waste_category_ids")
    @classmethod
    def validate_category_ids(
        cls,
        value: list[UUID] | None,
    ) -> list[UUID] | None:
        if value is None:
            return value

        if len(value) != len(set(value)):
            raise ValueError("Duplicate waste category IDs are not allowed")

        return value

    @model_validator(mode="after")
    def validate_update_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        return self


class RecyclingCenterStatusUpdate(BaseModel):
    status: RecyclingCenterStatus
    is_available: bool | None = None



from pydantic import computed_field


class RecyclingCenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: str | None

    location_id: UUID
    manager_user_id: UUID | None

    processing_capacity_kg_per_day: float
    is_available: bool
    status: RecyclingCenterStatus

    created_at: object
    updated_at: object

    @computed_field
    @property
    def accepted_waste_category_ids(self) -> list[UUID]:
        return [
            category.id
            for category in self.accepted_waste_categories
        ]

    accepted_waste_categories: list = Field(
        exclude=True,
        default_factory=list,
    )
