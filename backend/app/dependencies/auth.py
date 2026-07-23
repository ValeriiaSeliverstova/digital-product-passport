from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User
from app.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

MANUFACTURER_ROLE = "manufacturer_user"
SYSTEM_ADMIN_ROLE = "system_admin"


def authentication_error() -> HTTPException:
    """Create the standard response used for invalid authentication."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def authorization_error() -> HTTPException:
    """Create the response used when a user lacks the required role."""

    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Return the active database user identified by a valid access token."""

    try:
        user_id = decode_access_token(token)
    except InvalidTokenError:
        raise authentication_error() from None

    statement = (
        select(User)
        .options(joinedload(User.role))
        .where(User.id == user_id)
    )
    user = db.scalar(statement)

    if user is None or user.status != "active":
        raise authentication_error()

    return user


def require_manufacturer(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Allow only manufacturer users linked to an organization."""

    if (
        current_user.role.name != MANUFACTURER_ROLE
        or current_user.organization_id is None
    ):
        raise authorization_error()

    return current_user


def require_system_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Allow only platform-level system administrators."""

    if current_user.role.name != SYSTEM_ADMIN_ROLE:
        raise authorization_error()

    return current_user
