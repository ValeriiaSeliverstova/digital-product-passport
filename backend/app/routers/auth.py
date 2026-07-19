from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import authentication_error
from app.models import User
from app.schemas.auth import TokenResponse
from app.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Authenticate a user and return a short-lived bearer token."""

    email = form_data.username.strip().lower()
    statement = select(User).where(User.email == email)
    user = db.scalar(statement)

    if user is None:
        verify_password(form_data.password, DUMMY_PASSWORD_HASH)
        raise authentication_error()

    password_is_valid = verify_password(form_data.password, user.password_hash)
    if not password_is_valid or user.status != "active":
        raise authentication_error()

    # Authentication responses must not be stored by browsers or proxies.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return TokenResponse(access_token=create_access_token(user.id))
