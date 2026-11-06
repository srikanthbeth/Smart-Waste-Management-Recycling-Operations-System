from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128
    )


class TokenResponse(BaseModel):

    access_token: str

    refresh_token: str

    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):

    refresh_token: str


class PasswordResetRequest(BaseModel):

    email: EmailStr


class PasswordResetConfirm(BaseModel):

    token: str

    new_password: str = Field(
        min_length=8,
        max_length=128
    )


class ChangePasswordRequest(BaseModel):

    current_password: str

    new_password: str = Field(
        min_length=8,
        max_length=128
    )


class MessageResponse(BaseModel):

    message: str