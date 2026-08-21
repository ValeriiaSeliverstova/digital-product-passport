from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    SERVICE_TECHNICIAN_ROLE,
    require_manufacturer,
)
from app.email_delivery import (
    EmailDeliveryError,
    EmailNotConfiguredError,
    send_team_member_invitation_email,
)
from app.models import InvitationToken, Role, User
from app.schemas.team_member import (
    TeamMemberCreate,
    TeamMemberResponse,
    TeamMemberUpdate,
)
from app.security import (
    create_invitation_token,
    create_unusable_password_hash,
    hash_invitation_token,
)


router = APIRouter(
    prefix="/api/organizations/me/team-members",
    tags=["organization team members"],
)
DatabaseSession = Annotated[Session, Depends(get_db)]
OrganizationAdmin = Annotated[User, Depends(require_manufacturer)]
INVITATION_LIFETIME = timedelta(days=7)
# An invited technician waits here until the emailed link is used. Every
# authenticated path already requires "active", so the account stays unusable.
PENDING_STATUS = "pending"


def deliver_invitation(
    *,
    recipient: str,
    invitation_token: str,
    organization_name: str,
) -> None:
    """Send the invitation after the response has already been returned."""

    try:
        send_team_member_invitation_email(
            recipient=recipient,
            invitation_token=invitation_token,
            organization_name=organization_name,
        )
    except (EmailNotConfiguredError, EmailDeliveryError):
        pass


@router.get("", response_model=list[TeamMemberResponse])
def list_team_members(
    db: DatabaseSession,
    current_user: OrganizationAdmin,
) -> list[TeamMemberResponse]:
    """List service technicians in the administrator's organization."""

    members = db.scalars(
        select(User)
        .join(Role)
        .where(
            User.organization_id == current_user.organization_id,
            Role.name == SERVICE_TECHNICIAN_ROLE,
        )
        .order_by(User.email),
    ).all()
    return [_team_member_response(member) for member in members]


@router.post(
    "",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_team_member(
    data: TeamMemberCreate,
    background_tasks: BackgroundTasks,
    db: DatabaseSession,
    current_user: OrganizationAdmin,
) -> TeamMemberResponse:
    """Invite one technician to join the current organization by email."""

    role = db.scalar(select(Role).where(Role.name == SERVICE_TECHNICIAN_ROLE))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service technician role is not configured",
        )

    member = User(
        organization_id=current_user.organization_id,
        role_id=role.id,
        email=data.email,
        # The account has no usable password until the invitation is accepted.
        password_hash=create_unusable_password_hash(),
        status=PENDING_STATUS,
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from error
    db.refresh(member)

    issued_at = datetime.now(timezone.utc)
    raw_token = create_invitation_token()
    db.execute(
        update(InvitationToken)
        .where(
            InvitationToken.user_id == member.id,
            InvitationToken.used_at.is_(None),
        )
        .values(used_at=issued_at),
    )
    db.add(
        InvitationToken(
            user_id=member.id,
            token_hash=hash_invitation_token(raw_token),
            expires_at=issued_at + INVITATION_LIFETIME,
        ),
    )
    db.commit()

    background_tasks.add_task(
        deliver_invitation,
        recipient=member.email,
        invitation_token=raw_token,
        organization_name=(
            current_user.organization.name
            if current_user.organization is not None
            else "Your organization"
        ),
    )

    return _team_member_response(member)


@router.put("/{member_id}", response_model=TeamMemberResponse)
def update_team_member(
    member_id: UUID,
    data: TeamMemberUpdate,
    db: DatabaseSession,
    current_user: OrganizationAdmin,
) -> TeamMemberResponse:
    """Activate or deactivate an owned service-technician account."""

    member = db.scalar(
        select(User)
        .join(Role)
        .where(
            User.id == member_id,
            User.organization_id == current_user.organization_id,
            Role.name == SERVICE_TECHNICIAN_ROLE,
        ),
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found",
        )

    # Activating a pending invitation here would leave the technician with an
    # unusable password and no way to redeem their link, so refuse it.
    if member.status == PENDING_STATUS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This technician has not accepted their invitation yet",
        )

    member.status = data.status
    db.commit()
    db.refresh(member)
    return _team_member_response(member)


def _team_member_response(member: User) -> TeamMemberResponse:
    return TeamMemberResponse(
        id=member.id,
        email=member.email,
        status=member.status,
        role="service_technician",
    )
