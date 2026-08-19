from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import MANUFACTURER_ROLE, authentication_error
from app.email_delivery import (
    EmailDeliveryError,
    EmailNotConfiguredError,
    send_password_reset_email,
)
from app.models import Organization, PasswordResetToken, Role, User
from app.schemas.auth import (
    AuthMessageResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_password_reset_token,
    hash_password,
    hash_password_reset_token,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["authentication"])

FORGOT_PASSWORD_MESSAGE = (
    "If an account with this email exists, password reset instructions have "
    "been sent."
)
RESET_PASSWORD_MESSAGE = "Your password has been reset successfully."
INVALID_RESET_TOKEN_MESSAGE = "Password reset link is invalid or has expired."
DUPLICATE_EMAIL_MESSAGE = "An account with this email already exists."
PASSWORD_RESET_LIFETIME = timedelta(minutes=30)


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    data: SignupRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SignupResponse:
    """Register a manufacturer organization and its first administrator."""

    # The role is resolved on the server, so a public request can never choose
    # it and can never create a system administrator.
    role = db.scalar(select(Role).where(Role.name == MANUFACTURER_ROLE))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable",
        )

    if db.scalar(select(User).where(User.email == data.email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_EMAIL_MESSAGE,
        )

    organization = Organization(name=data.organization_name)
    user = User(
        organization=organization,
        role=role,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        password_hash=hash_password(data.password.get_secret_value()),
        status="active",
    )
    db.add(user)

    # Both rows are written in one transaction, so a lost race on the unique
    # email constraint rolls back the organization instead of orphaning it.
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_EMAIL_MESSAGE,
        ) from error

    db.refresh(user)
    return SignupResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        status=user.status,
        role=role.name,
        organization_id=organization.id,
        organization_name=organization.name,
    )


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


def deliver_password_reset_email(*, recipient: str, reset_token: str) -> None:
    """Send the reset email after the response has already been returned."""

    # Delivery problems must stay invisible to the caller, and an unhandled
    # error here would surface as a failed background task rather than a
    # useful signal, so both configuration and transport failures are ignored.
    try:
        send_password_reset_email(recipient=recipient, reset_token=reset_token)
    except (EmailNotConfiguredError, EmailDeliveryError):
        pass


@router.post("/forgot-password", response_model=AuthMessageResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> AuthMessageResponse:
    """Create and email a reset token without disclosing account existence."""

    user = db.scalar(
        select(User).where(User.email == data.email, User.status == "active"),
    )
    if user is None:
        return AuthMessageResponse(message=FORGOT_PASSWORD_MESSAGE)

    requested_at = datetime.now(timezone.utc)
    raw_token = create_password_reset_token()
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=requested_at),
    )
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_password_reset_token(raw_token),
            expires_at=requested_at + PASSWORD_RESET_LIFETIME,
        ),
    )
    db.commit()

    # SMTP delivery can take seconds, while an unknown address returns
    # immediately. Sending after the response keeps both paths equally fast so
    # response time cannot be used to discover which accounts exist.
    background_tasks.add_task(
        deliver_password_reset_email,
        recipient=user.email,
        reset_token=raw_token,
    )

    return AuthMessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=AuthMessageResponse)
def reset_password(
    data: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthMessageResponse:
    """Replace a password after validating a single-use reset token."""

    now = datetime.now(timezone.utc)
    reset_token = db.scalar(
        select(PasswordResetToken)
        .join(User, User.id == PasswordResetToken.user_id)
        .where(
            PasswordResetToken.token_hash
            == hash_password_reset_token(data.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
            User.status == "active",
        ),
    )
    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN_MESSAGE,
        )

    # Claim the token atomically so two concurrent requests cannot reuse it.
    claimed = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.id == reset_token.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .values(used_at=now),
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN_MESSAGE,
        )

    user = db.get(User, reset_token.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_RESET_TOKEN_MESSAGE,
        )

    user.password_hash = hash_password(data.new_password.get_secret_value())
    # Mark any other still-active tokens for the user as consumed.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now),
    )
    db.commit()

    return AuthMessageResponse(message=RESET_PASSWORD_MESSAGE)
