from typing import Annotated

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_manufacturer
from app.models import Organization, User
from app.schemas.organization import OrganizationResponse, OrganizationUpdate


router = APIRouter(prefix="/api/organizations", tags=["organizations"])

MAX_LOGO_BYTES = 2 * 1024 * 1024


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


@router.put("/me/logo", response_model=OrganizationResponse)
async def upload_current_organization_logo(
    current_user: Annotated[User, Depends(require_manufacturer)],
    db: Annotated[Session, Depends(get_db)],
    logo: Annotated[UploadFile, File()],
) -> Organization:
    """Upload a small raster logo for the current manufacturer."""

    logo_data = await logo.read(MAX_LOGO_BYTES + 1)
    if len(logo_data) > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Organization logo must not exceed 2 MB",
        )

    content_type = detect_logo_content_type(logo_data)
    if content_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Organization logo must be a PNG, JPEG, or WebP image",
        )

    organization = get_current_organization(db, current_user)
    organization.logo_data = logo_data
    organization.logo_content_type = content_type
    organization.logo_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(organization)
    return organization


@router.delete("/me/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_organization_logo(
    current_user: Annotated[User, Depends(require_manufacturer)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Remove the current manufacturer's logo."""

    organization = get_current_organization(db, current_user)
    organization.logo_data = None
    organization.logo_content_type = None
    organization.logo_updated_at = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{organization_id}/logo", response_class=Response)
def get_organization_logo(
    organization_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Return a public organization logo for display in product interfaces."""

    organization = db.get(Organization, organization_id)
    if organization is None or organization.logo_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization logo not found",
        )
    return Response(
        content=organization.logo_data,
        media_type=organization.logo_content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


def get_current_organization(db: Session, current_user: User) -> Organization:
    """Load the authenticated manufacturer's organization."""

    organization = db.get(Organization, current_user.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return organization


def detect_logo_content_type(data: bytes) -> str | None:
    """Recognize supported image formats from file bytes, not its filename."""

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
