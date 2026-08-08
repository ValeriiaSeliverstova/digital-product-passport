from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_manufacturer
from app.models import Organization, User
from app.schemas.organization import OrganizationResponse, OrganizationUpdate


router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.put("/me", response_model=OrganizationResponse)
def update_current_organization(
    data: OrganizationUpdate,
    current_user: Annotated[User, Depends(require_manufacturer)],
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    """Update only the organization owned by the authenticated manufacturer."""

    organization = db.get(Organization, current_user.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(organization, field, value)

    db.commit()
    db.refresh(organization)
    return organization
