from pydantic import BaseModel, EmailStr, Field
from app.types.user import UserResponse


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Name must be at least 1 character")
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse