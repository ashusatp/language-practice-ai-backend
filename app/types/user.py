import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    is_active: bool
    is_email_verified: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
