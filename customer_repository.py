
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.customer import Customer
from schemas.customer import CustomerCreate, CustomerUpdate


class CustomerRepository:

    @staticmethod
    def create(
        db: Session,
        user_id: uuid.UUID,
        customer_code: str,
        customer_data: CustomerCreate,
    ) -> Customer:
        customer = Customer(
            user_id=user_id,
            customer_code=customer_code,
            **customer_data.model_dump(),
        )

        db.add(customer)
        db.commit()
        db.refresh(customer)

        return customer

    @staticmethod
    def get_by_id(
        db: Session,
        customer_id: uuid.UUID,
    ) -> Customer | None:
        return db.scalar(
            select(Customer).where(
                Customer.id == customer_id
            )
        )

    @staticmethod
    def get_by_user_id(
        db: Session,
        user_id: uuid.UUID,
    ) -> Customer | None:
        return db.scalar(
            select(Customer).where(
                Customer.user_id == user_id
            )
        )

    @staticmethod
    def get_by_customer_code(
        db: Session,
        customer_code: str,
    ) -> Customer | None:
        return db.scalar(
            select(Customer).where(
                Customer.customer_code == customer_code
            )
        )

    @staticmethod
    def list_all(
        db: Session,
        customer_type=None,
        customer_status=None,
        location_id: uuid.UUID | None = None,
        city: str | None = None,
    ) -> list[Customer]:
        statement = select(Customer)

        if customer_type is not None:
            statement = statement.where(
                Customer.customer_type == customer_type
            )

        if customer_status is not None:
            statement = statement.where(
                Customer.status == customer_status
            )

        if location_id is not None:
            statement = statement.where(
                Customer.location_id == location_id
            )

        if city is not None:
            statement = statement.where(
                Customer.city.ilike(f"%{city}%")
            )

        statement = statement.order_by(
            Customer.created_at.desc()
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def update(
        db: Session,
        customer: Customer,
        update_data: CustomerUpdate,
    ) -> Customer:
        values = update_data.model_dump(exclude_unset=True)

        for field, value in values.items():
            setattr(customer, field, value)

        db.commit()
        db.refresh(customer)

        return customer

    @staticmethod
    def update_status(
        db: Session,
        customer: Customer,
        customer_status,
    ) -> Customer:
        customer.status = customer_status

        db.commit()
        db.refresh(customer)

        return customer
