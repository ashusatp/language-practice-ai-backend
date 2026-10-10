from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def get_my_profile(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
    }