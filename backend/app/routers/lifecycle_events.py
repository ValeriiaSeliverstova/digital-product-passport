from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_product_item_member
from app.models import LifecycleEvent, ProductItem, User
from app.schemas.lifecycle_event import (
    LifecycleEventCreate,
    LifecycleEventResponse,
)


router = APIRouter(
    prefix="/api/product-items/{item_id}/lifecycle-events",
    tags=["lifecycle events"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]
ProductItemMember = Annotated[User, Depends(require_product_item_member)]


@router.post(
    "",
    response_model=LifecycleEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lifecycle_event(
    item_id: UUID,
    data: LifecycleEventCreate,
    db: DatabaseSession,
    current_user: ProductItemMember,
) -> LifecycleEvent:
    """Append an event to an owned published or retired product item."""

    product_item = get_owned_product_item(
        db,
        item_id,
        current_user.organization_id,
    )
    if product_item.status == "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lifecycle events require a published product item",
        )

    lifecycle_event = LifecycleEvent(
        item_id=product_item.id,
        created_by_user_id=current_user.id,
        **data.model_dump(),
    )
    db.add(lifecycle_event)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lifecycle event could not be created",
        ) from error

    db.refresh(lifecycle_event)
    return lifecycle_event


@router.get("", response_model=list[LifecycleEventResponse])
def list_lifecycle_events(
    item_id: UUID,
    db: DatabaseSession,
    current_user: ProductItemMember,
) -> list[LifecycleEvent]:
    """List an owned product item's complete history, newest first."""

    product_item = get_owned_product_item(
        db,
        item_id,
        current_user.organization_id,
    )
    statement = (
        select(LifecycleEvent)
        .where(LifecycleEvent.item_id == product_item.id)
        .order_by(
            LifecycleEvent.occurred_at.desc(),
            LifecycleEvent.created_at.desc(),
        )
    )
    return list(db.scalars(statement).all())


def get_owned_product_item(
    db: Session,
    item_id: UUID,
    organization_id: UUID | None,
) -> ProductItem:
    """Load the item only when it belongs to the current manufacturer."""

    product_item = db.scalar(
        select(ProductItem).where(
            ProductItem.id == item_id,
            ProductItem.organization_id == organization_id,
        ),
    )
    if product_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product item not found",
        )
    return product_item
