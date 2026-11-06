from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import (
    ComplaintCategory,
    ComplaintPriority,
    ComplaintStatus,
)


class CustomerComplaintCreate(BaseModel):
    category: ComplaintCategory
    priority: ComplaintPriority = ComplaintPriority.MEDIUM
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)


class CustomerComplaintUpdate(BaseModel):
    category: ComplaintCategory | None = None
    priority: ComplaintPriority | None = None
    status: ComplaintStatus | None = None
    assigned_team: str | None = Field(default=None, max_length=100)
    assigned_to_user_id: UUID | None = None
    resolution_remarks: str | None = None


class CustomerComplaintResponse(BaseModel):
    id: UUID
    complaint_number: str
    customer_id: UUID
    category: ComplaintCategory
    priority: ComplaintPriority
    status: ComplaintStatus
    subject: str
    description: str
    assigned_team: str | None
    assigned_to_user_id: UUID | None
    resolution_remarks: str | None
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintHistoryResponse(BaseModel):
    id: UUID
    complaint_id: UUID
    previous_status: ComplaintStatus | None
    new_status: ComplaintStatus
    remarks: str | None
    changed_by_user_id: UUID
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)