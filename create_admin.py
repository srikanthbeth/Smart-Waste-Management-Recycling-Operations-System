from getpass import getpass

from sqlalchemy import select

from db.session import SessionLocal
from models.user import User
from core.constants import UserRole
from core.security import hash_password
from core.config import settings


def create_super_admin():

    db = SessionLocal()

    try:

        email = settings.BOOTSTRAP_ADMIN_EMAIL.lower().strip()

        existing_admin = db.scalar(
            select(User).where(
                User.email == email
            )
        )

        if existing_admin:

            print("Admin account already exists.")
            return

        password = getpass("Enter Super Admin password: ")
        confirm_password = getpass("Confirm Super Admin password: ")

        if password != confirm_password:

            print("Passwords do not match.")
            return

        from services.auth_service import AuthService

        AuthService.validate_password(password)

        admin = User(
            full_name="System Administrator",
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True
        )

        db.add(admin)
        db.commit()

        print("Super Admin created successfully.")

    except Exception as error:

        db.rollback()
        print("Error:", error)

    finally:

        db.close()


if __name__ == "__main__":
    create_super_admin()