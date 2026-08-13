from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    SERVICE_TECHNICIAN_ROLE,
    require_manufacturer,
)
from app.models import Role, User
from app.schemas.team_member import (
    TeamMemberCreate,
    TeamMemberResponse,
    TeamMemberUpdate,
)
from app.security import hash_password


router = APIRouter(
    prefix="/api/organizations/me/team-members",
    tags=["organization team members"],
)
DatabaseSession = Annotated[Session, Depends(get_db)]
OrganizationAdmin = Annotated[User, Depends(require_manufacturer)]


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
    db: DatabaseSession,
    current_user: OrganizationAdmin,
) -> TeamMemberResponse:
    """Create one technician account inside the current organization."""

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
        password_hash=hash_password(data.initial_password.get_secret_value()),
        status="active",
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
