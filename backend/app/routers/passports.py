from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.azure_devops import (
    AzureDevOpsNotConfiguredError,
    AzureDevOpsRequestError,
    create_support_work_item,
    support_ticket_is_enabled,
)
from app.config import settings
from app.models import Organization, PassportTemplate, ProductItem, ProductModel
from app.schemas.public_passport import (
    PublicLifecycleEvent,
    PublicPassportField,
    PublicPassportResponse,
)
from app.schemas.support_ticket import SupportTicketCreate, SupportTicketResponse


router = APIRouter(prefix="/api/passports", tags=["public passports"])

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/{public_id}", response_model=PublicPassportResponse)
def get_public_passport(
    public_id: UUID,
    db: DatabaseSession,
) -> PublicPassportResponse:
    """Return public fields for one published product passport."""

    product_item = get_published_product_item(db, public_id)
    if product_item is None:
        # The same response hides missing, Draft, and Retired passports.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published passport not found",
        )

    product_model = product_item.product_model
    template = product_model.template
    organization = product_item.organization
    public_fields = [
        PublicPassportField(
            code=field.code,
            label=field.label,
            data_type=field.data_type,
            value=product_item.passport_data[field.code],
        )
        for field in template.fields
        if field.access_level == "public"
        and field.code in product_item.passport_data
        and product_item.passport_data[field.code] is not None
    ]
    public_events = [
        PublicLifecycleEvent.model_validate(event, from_attributes=True)
        for event in sorted(
            product_item.lifecycle_events,
            key=lambda lifecycle_event: lifecycle_event.occurred_at,
            reverse=True,
        )
        if event.access_level == "public"
    ]

    return PublicPassportResponse(
        public_id=product_item.public_id,
        manufacturer_name=organization.name,
        manufacturer_logo_path=get_logo_path(organization),
        support_email=organization.contact_email,
        support_phone=organization.phone,
        support_website=organization.website,
        support_ticket_enabled=support_ticket_is_enabled(
            organization.azure_devops_area_path,
            organization.azure_devops_work_item_type,
        ),
        category_name=product_model.category.name,
        model_code=product_model.model_code,
        model_name=product_model.name,
        model_description=product_model.description,
        model_image_path=get_product_model_image_path(product_model),
        template_name=template.name,
        template_version=template.version,
        serial_number=product_item.serial_number,
        manufacture_date=product_item.manufacture_date,
        fields=public_fields,
        lifecycle_events=public_events,
    )


@router.post(
    "/{public_id}/support-tickets",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_support_ticket(
    public_id: UUID,
    data: SupportTicketCreate,
    db: DatabaseSession,
) -> SupportTicketResponse:
    """Create an Azure DevOps ticket for one published product passport."""

    product_item = get_published_product_item(db, public_id)
    if product_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published passport not found",
        )

    product_model = product_item.product_model
    organization = product_item.organization
    try:
        ticket_id, ticket_url = create_support_work_item(
            area_path=organization.azure_devops_area_path,
            work_item_type=organization.azure_devops_work_item_type,
            requester_name=data.requester_name,
            requester_email=data.requester_email,
            subject=data.subject,
            message=data.message,
            manufacturer_name=organization.name,
            category_name=product_model.category.name,
            model_code=product_model.model_code,
            model_name=product_model.name,
            serial_number=product_item.serial_number,
            public_id=str(product_item.public_id),
            passport_url=(
                f"{settings.frontend_origin}/passport/{product_item.public_id}"
            ),
        )
    except AzureDevOpsNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Support ticket service is not configured",
        ) from error
    except AzureDevOpsRequestError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Support ticket could not be submitted",
        ) from error

    return SupportTicketResponse(ticket_id=ticket_id, ticket_url=ticket_url)


def get_published_product_item(
    db: Session,
    public_id: UUID,
) -> ProductItem | None:
    """Load the complete public-passport graph for one published item."""

    return db.scalar(
        select(ProductItem)
        .options(
            joinedload(ProductItem.organization),
            joinedload(ProductItem.product_model).joinedload(
                ProductModel.category,
            ),
            joinedload(ProductItem.product_model)
            .joinedload(ProductModel.template)
            .selectinload(PassportTemplate.fields),
            selectinload(ProductItem.lifecycle_events),
        )
        .where(
            ProductItem.public_id == public_id,
            ProductItem.status == "published",
        ),
    )


def get_logo_path(organization: Organization) -> str | None:
    """Build a cache-safe public path only when the organization has a logo."""

    if not organization.has_logo:
        return None

    path = f"/api/organizations/{organization.id}/logo"
    if organization.logo_updated_at is not None:
        return f"{path}?v={int(organization.logo_updated_at.timestamp())}"
    return path


def get_product_model_image_path(product_model: ProductModel) -> str | None:
    """Build a cache-safe path when the product model has an image."""

    if not product_model.has_image:
        return None

    path = f"/api/product-models/{product_model.id}/image"
    if product_model.image_updated_at is not None:
        return f"{path}?v={int(product_model.image_updated_at.timestamp())}"
    return path
