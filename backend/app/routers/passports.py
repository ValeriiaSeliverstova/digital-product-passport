from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.models import PassportTemplate, ProductItem, ProductModel
from app.schemas.public_passport import (
    PublicLifecycleEvent,
    PublicPassportField,
    PublicPassportResponse,
)


router = APIRouter(prefix="/api/passports", tags=["public passports"])

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/{public_id}", response_model=PublicPassportResponse)
def get_public_passport(
    public_id: UUID,
    db: DatabaseSession,
) -> PublicPassportResponse:
    """Return public fields for one published product passport."""

    product_item = db.scalar(
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
    if product_item is None:
        # The same response hides missing, Draft, and Retired passports.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published passport not found",
        )

    product_model = product_item.product_model
    template = product_model.template
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
        manufacturer_name=product_item.organization.name,
        category_name=product_model.category.name,
        model_code=product_model.model_code,
        model_name=product_model.name,
        model_description=product_model.description,
        template_name=template.name,
        template_version=template.version,
        serial_number=product_item.serial_number,
        manufacture_date=product_item.manufacture_date,
        fields=public_fields,
        lifecycle_events=public_events,
    )
