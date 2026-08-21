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
    send_email_confirmation_email,
    send_password_reset_email,
)
from app.models import (
    EmailConfirmationToken,
    InvitationToken,
    Organization,
    PasswordResetToken,
    Role,
    User,
)
from app.schemas.auth import (
    AcceptInvitationRequest,
    AuthMessageResponse,
    ConfirmEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_email_confirmation_token,
    create_password_reset_token,
    hash_email_confirmation_token,
    hash_invitation_token,
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
CONFIRM_EMAIL_MESSAGE = "Your email address is confirmed. You can now sign in."
INVALID_CONFIRMATION_MESSAGE = (
    "This confirmation link is invalid or has expired."
)
RESEND_CONFIRMATION_MESSAGE = (
    "If this account exists and is not confirmed, a new confirmation email "
    "has been sent."
)
ACCEPT_INVITATION_MESSAGE = "Your password is set. You can now sign in."
INVALID_INVITATION_MESSAGE = "This invitation link is invalid or has expired."
PASSWORD_RESET_LIFETIME = timedelta(minutes=30)
EMAIL_CONFIRMATION_LIFETIME = timedelta(hours=24)
# Signup accounts wait in this state until the emailed link is opened. Every
# authenticated path already requires "active", so nothing else needs changing.
PENDING_STATUS = "pending"


def deliver_email_confirmation(*, recipient: str, confirmation_token: str) -> None:
    """Send the confirmation email after the response has been returned."""

    try:
        send_email_confirmation_email(
            recipient=recipient,
            confirmation_token=confirmation_token,
        )
    except (EmailNotConfiguredError, EmailDeliveryError):
        pass


def issue_email_confirmation(
    db: Session,
    user: User,
    background_tasks: BackgroundTasks,
) -> None:
    """Invalidate older confirmation tokens and email a fresh single-use one."""

    issued_at = datetime.now(timezone.utc)
    raw_token = create_email_confirmation_token()
    db.execute(
        update(EmailConfirmationToken)
        .where(
            EmailConfirmationToken.user_id == user.id,
            EmailConfirmationToken.used_at.is_(None),
        )
        .values(used_at=issued_at),
    )
    db.add(
        EmailConfirmationToken(
            user_id=user.id,
            token_hash=hash_email_confirmation_token(raw_token),
            expires_at=issued_at + EMAIL_CONFIRMATION_LIFETIME,
        ),
    )
    db.commit()

    background_tasks.add_task(
        deliver_email_confirmation,
        recipient=user.email,
        confirmation_token=raw_token,
    )


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    data: SignupRequest,
    background_tasks: BackgroundTasks,
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
        status=PENDING_STATUS,
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
    issue_email_confirmation(db, user, background_tasks)

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


@router.post("/accept-invitation", response_model=AuthMessageResponse)
def accept_invitation(
    data: AcceptInvitationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthMessageResponse:
    """Let an invited technician set their first password and activate."""

    now = datetime.now(timezone.utc)
    invitation = db.scalar(
        select(InvitationToken).where(
            InvitationToken.token_hash == hash_invitation_token(data.token),
            InvitationToken.used_at.is_(None),
            InvitationToken.expires_at > now,
        ),
    )
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_INVITATION_MESSAGE,
        )

    # Claim the token atomically so it cannot be redeemed twice.
    claimed = db.execute(
        update(InvitationToken)
        .where(
            InvitationToken.id == invitation.id,
            InvitationToken.used_at.is_(None),
            InvitationToken.expires_at > now,
        )
        .values(used_at=now),
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_INVITATION_MESSAGE,
        )

    user = db.get(User, invitation.user_id)
    # Only a pending invitation activates an account, so an old link can never
    # reset the password of a technician an administrator later deactivated.
    if user is None or user.status != PENDING_STATUS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_INVITATION_MESSAGE,
        )

    user.password_hash = hash_password(data.new_password.get_secret_value())
    user.status = "active"
    db.commit()

    return AuthMessageResponse(message=ACCEPT_INVITATION_MESSAGE)


@router.post("/confirm-email", response_model=AuthMessageResponse)
def confirm_email(
    data: ConfirmEmailRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthMessageResponse:
    """Activate a pending account after validating its confirmation token."""

    now = datetime.now(timezone.utc)
    confirmation = db.scalar(
        select(EmailConfirmationToken).where(
            EmailConfirmationToken.token_hash
            == hash_email_confirmation_token(data.token),
            EmailConfirmationToken.used_at.is_(None),
            EmailConfirmationToken.expires_at > now,
        ),
    )
    if confirmation is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_CONFIRMATION_MESSAGE,
        )

    # Claim the token atomically so two concurrent clicks cannot both succeed.
    claimed = db.execute(
        update(EmailConfirmationToken)
        .where(
            EmailConfirmationToken.id == confirmation.id,
            EmailConfirmationToken.used_at.is_(None),
            EmailConfirmationToken.expires_at > now,
        )
        .values(used_at=now),
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_CONFIRMATION_MESSAGE,
        )

    user = db.get(User, confirmation.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_CONFIRMATION_MESSAGE,
        )

    # Only a pending account is activated. A deactivated account must never be
    # re-enabled by an old confirmation link.
    if user.status == PENDING_STATUS:
        user.status = "active"
    db.commit()

    return AuthMessageResponse(message=CONFIRM_EMAIL_MESSAGE)


@router.post("/resend-confirmation", response_model=AuthMessageResponse)
def resend_confirmation(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> AuthMessageResponse:
    """Email a fresh confirmation link so an expired one is not a dead end."""

    user = db.scalar(
        select(User).where(
            User.email == data.email,
            User.status == PENDING_STATUS,
        ),
    )
    # The reply never changes, so this cannot be used to discover accounts.
    if user is not None:
        issue_email_confirmation(db, user, background_tasks)

    return AuthMessageResponse(message=RESEND_CONFIRMATION_MESSAGE)


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
