from uuid import UUID

from sqlalchemy.orm import Session

from models.customer_complaint import CustomerComplaint, ComplaintHistory
from core.constants import ComplaintStatus, ComplaintPriority, ComplaintCategory


class CustomerComplaintRepository:

    @staticmethod
    def create(db: Session, complaint: CustomerComplaint, history: ComplaintHistory):
        db.add(complaint)
        db.flush()

        history.complaint_id = complaint.id
        db.add(history)

        db.commit()
        db.refresh(complaint)
        return complaint

    @staticmethod
    def get_by_id(db: Session, complaint_id: UUID):
        return (
            db.query(CustomerComplaint)
            .filter(CustomerComplaint.id == complaint_id)
            .first()
        )

    @staticmethod
    def list_all(
        db: Session,
        customer_id: UUID | None = None,
        status: ComplaintStatus | None = None,
        priority: ComplaintPriority | None = None,
        category: ComplaintCategory | None = None,
    ):
        query = db.query(CustomerComplaint)

        if customer_id:
            query = query.filter(CustomerComplaint.customer_id == customer_id)

        if status:
            query = query.filter(CustomerComplaint.status == status)

        if priority:
            query = query.filter(CustomerComplaint.priority == priority)

        if category:
            query = query.filter(CustomerComplaint.category == category)

        return query.order_by(CustomerComplaint.created_at.desc()).all()

    @staticmethod
    def update(
        db: Session,
        complaint: CustomerComplaint,
        history: ComplaintHistory | None = None,
    ):
        db.add(complaint)

        if history:
            db.add(history)

        db.commit()
        db.refresh(complaint)
        return complaint

    @staticmethod
    def get_history(db: Session, complaint_id: UUID):
        return (
            db.query(ComplaintHistory)
            .filter(ComplaintHistory.complaint_id == complaint_id)
            .order_by(ComplaintHistory.changed_at.asc())
            .all()
        )