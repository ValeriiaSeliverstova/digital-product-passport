from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.user import PasswordChangeRequest, UserResponse
from app.security import hash_password, verify_password


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return the currently authenticated user."""

    return current_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_current_user_password(
    password_change: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Replace the authenticated user's password after verifying the old one."""

    current_password = password_change.current_password.get_secret_value()
    new_password = password_change.new_password.get_secret_value()

    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if verify_password(new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    current_user.password_hash = hash_password(new_password)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
