from fastapi import Depends

from core.constants import UserRole
from core.exceptions import PermissionDeniedError


def require_roles(*allowed_roles: UserRole):

    from routes.auth import get_current_user

    def role_checker(
        current_user=Depends(get_current_user)
    ):

        if current_user.role not in allowed_roles:

            raise PermissionDeniedError(
                "You are not authorized to perform this action"
            )

        return current_user

    return role_checker