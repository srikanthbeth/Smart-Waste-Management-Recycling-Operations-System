from fastapi import HTTPException, status


class AuthenticationError(HTTPException):

    def __init__(self, detail="Invalid authentication credentials"):

        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class PermissionDeniedError(HTTPException):

    def __init__(self, detail="You do not have permission"):

        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class ResourceNotFoundError(HTTPException):

    def __init__(self, detail="Resource not found"):

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ConflictError(HTTPException):

    def __init__(self, detail="Resource already exists"):

        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )