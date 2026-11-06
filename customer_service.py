
from uuid import uuid4, UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import (
    CustomerStatus,
    CustomerType,
    LocationStatus,
    UserRole,
)
from models.location import Location
from models.user import User
from repositories.customer_repository import CustomerRepository
from schemas.customer import CustomerCreate, CustomerUpdate


ORGANIZATION_TYPES = {
    CustomerType.COMMERCIAL,
    CustomerType.INDUSTRIAL,
    CustomerType.INSTITUTIONAL,
}


class CustomerService:

    @staticmethod
    def validate_location(
        db: Session,
        location_id: UUID | None,
    ):
        if location_id is None:
            return

        location = db.get(Location, location_id)

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service location not found",
            )

        if (
            location.status != LocationStatus.ACTIVE
            or not location.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected service location is inactive",
            )

    @staticmethod
    def create_customer(
        db: Session,
        current_user: User,
        customer_data: CustomerCreate,
    ):
        if current_user.role != UserRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only customer users can create customer profiles",
            )

        existing_customer = CustomerRepository.get_by_user_id(
            db,
            current_user.id,
        )

        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer profile already exists for this user",
            )

        CustomerService.validate_location(
            db,
            customer_data.location_id,
        )

        customer_code = f"CUST-{uuid4().hex[:12].upper()}"

        try:
            return CustomerRepository.create(
                db,
                current_user.id,
                customer_code,
                customer_data,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer profile already exists or customer code conflicts",
            )

    @staticmethod
    def get_my_customer_profile(
        db: Session,
        current_user: User,
    ):
        customer = CustomerRepository.get_by_user_id(
            db,
            current_user.id,
        )

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer profile not found",
            )

        return customer

    @staticmethod
    def get_customer(
        db: Session,
        customer_id: UUID,
    ):
        customer = CustomerRepository.get_by_id(
            db,
            customer_id,
        )

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )

        return customer

    @staticmethod
    def get_customer_for_user(
        db: Session,
        customer_id: UUID,
        current_user: User,
    ):
        customer = CustomerService.get_customer(
            db,
            customer_id,
        )

        management_roles = {
            UserRole.SUPER_ADMIN,
            UserRole.OPERATIONS_MANAGER,
            UserRole.COLLECTION_SUPERVISOR,
        }

        if (
            current_user.role not in management_roles
            and customer.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access another customer's profile",
            )

        return customer

    @staticmethod
    def list_customers(
        db: Session,
        customer_type=None,
        customer_status=None,
        location_id: UUID | None = None,
        city: str | None = None,
    ):
        return CustomerRepository.list_all(
            db,
            customer_type=customer_type,
            customer_status=customer_status,
            location_id=location_id,
            city=city,
        )

    @staticmethod
    def update_customer(
        db: Session,
        customer_id: UUID,
        current_user: User,
        update_data: CustomerUpdate,
    ):
        customer = CustomerService.get_customer_for_user(
            db,
            customer_id,
            current_user,
        )

        if customer.status == CustomerStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Suspended customer profiles cannot be updated",
            )

        values = update_data.model_dump(exclude_unset=True)

        if not values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update fields provided",
            )

        new_type = values.get(
            "customer_type",
            customer.customer_type,
        )

        new_organization_name = values.get(
            "organization_name",
            customer.organization_name,
        )

        if new_type in ORGANIZATION_TYPES and not new_organization_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Organization name is required for this customer type",
            )

        if (
            new_type == CustomerType.RESIDENTIAL
            and new_organization_name
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Residential customers cannot have an organization name",
            )

        if "location_id" in values:
            CustomerService.validate_location(
                db,
                values["location_id"],
            )

        try:
            return CustomerRepository.update(
                db,
                customer,
                update_data,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to update customer profile",
            )

    @staticmethod
    def update_customer_status(
        db: Session,
        customer_id: UUID,
        customer_status: CustomerStatus,
    ):
        customer = CustomerService.get_customer(
            db,
            customer_id,
        )

        return CustomerRepository.update_status(
            db,
            customer,
            customer_status,
        )
