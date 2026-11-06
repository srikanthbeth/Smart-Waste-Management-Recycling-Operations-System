from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.user import User
from models.customer_complaint import CustomerComplaint, ComplaintHistory

from core.constants import (
    UserRole,
    ComplaintStatus,
)

from schemas.customer_complaint import CustomerComplaintCreate, CustomerComplaintUpdate

from repositories.customer_complaint_repository import (
    CustomerComplaintRepository,
)


class CustomerComplaintService:

    @staticmethod
    def create_complaint(
        db: Session,
        payload: CustomerComplaintCreate,
        current_user: User,
    ):
        complaint = CustomerComplaint(
            complaint_number=f"CC-{uuid4().hex[:10].upper()}",
            customer_id=current_user.id,
            category=payload.category,
            priority=payload.priority,
            status=ComplaintStatus.OPEN,
            subject=payload.subject.strip(),
            description=payload.description.strip(),
        )

        history = ComplaintHistory(
            previous_status=None,
            new_status=ComplaintStatus.OPEN,
            remarks="Complaint created",
            changed_by_user_id=current_user.id,
        )

        return CustomerComplaintRepository.create(db, complaint, history)

    @staticmethod
    def get_complaint(
        db: Session,
        complaint_id: UUID,
        current_user: User,
    ):
        complaint = CustomerComplaintRepository.get_by_id(db, complaint_id)

        if not complaint:
            raise HTTPException(
                status_code=404,
                detail="Complaint not found",
            )

        if (
            current_user.role == UserRole.CUSTOMER
            and complaint.customer_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You cannot access another customer's complaint",
            )

        return complaint

    @staticmethod
    def list_complaints(
        db: Session,
        current_user: User,
        complaint_status=None,
        priority=None,
        category=None,
    ):
        customer_id = (
            current_user.id
            if current_user.role == UserRole.CUSTOMER
            else None
        )

        return CustomerComplaintRepository.list_all(
            db,
            customer_id=customer_id,
            status=complaint_status,
            priority=priority,
            category=category,
        )

    @staticmethod
    def update_complaint(
        db: Session,
        complaint_id: UUID,
        payload: CustomerComplaintUpdate,
        current_user: User,
    ):
        complaint = CustomerComplaintRepository.get_by_id(db, complaint_id)

        if not complaint:
            raise HTTPException(
                status_code=404,
                detail="Complaint not found",
            )

        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            return complaint

        if "assigned_to_user_id" in update_data:
            assigned_user_id = update_data["assigned_to_user_id"]

            if assigned_user_id is not None:
                assigned_user = (
                    db.query(User)
                    .filter(User.id == assigned_user_id)
                    .first()
                )

                if not assigned_user:
                    raise HTTPException(
                        status_code=404,
                        detail="Assigned user not found",
                    )

        old_status = complaint.status
        old_remarks = complaint.resolution_remarks

        new_status = update_data.get("status", old_status)
        new_remarks = update_data.get(
            "resolution_remarks",
            old_remarks,
        )

        if (
            new_status in (
                ComplaintStatus.RESOLVED,
                ComplaintStatus.CLOSED,
            )
            and not new_remarks
        ):
            raise HTTPException(
                status_code=400,
                detail="Resolution remarks are required to resolve or close a complaint",
            )

        for field, value in update_data.items():
            setattr(complaint, field, value)

        now = datetime.now(timezone.utc)

        if new_status == ComplaintStatus.RESOLVED:
            complaint.resolved_at = now

        if new_status == ComplaintStatus.CLOSED:
            complaint.closed_at = now

            if not complaint.resolved_at:
                complaint.resolved_at = now

        history_required = (
            old_status != complaint.status
            or old_remarks != complaint.resolution_remarks
            or "assigned_to_user_id" in update_data
            or "assigned_team" in update_data
        )

        history = None

        if history_required:
            history = ComplaintHistory(
                complaint_id=complaint.id,
                previous_status=old_status,
                new_status=complaint.status,
                remarks=(
                    complaint.resolution_remarks
                    or "Complaint details updated"
                ),
                changed_by_user_id=current_user.id,
            )

        return CustomerComplaintRepository.update(
            db,
            complaint,
            history,
        )

    @staticmethod
    def get_complaint_history(
        db: Session,
        complaint_id: UUID,
        current_user: User,
    ):
        complaint = CustomerComplaintService.get_complaint(
            db,
            complaint_id,
            current_user,
        )

        return CustomerComplaintRepository.get_history(
            db,
            complaint.id,
        )