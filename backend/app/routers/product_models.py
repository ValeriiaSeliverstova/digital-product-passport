from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_manufacturer
from app.models import PassportTemplate, ProductCategory, ProductModel, User
from app.schemas.product_model import (
    ProductModelCreate,
    ProductModelResponse,
    ProductModelUpdate,
)


router = APIRouter(prefix="/api/product-models", tags=["product models"])

DatabaseSession = Annotated[Session, Depends(get_db)]
Manufacturer = Annotated[User, Depends(require_manufacturer)]


@router.post(
    "",
    response_model=ProductModelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_model(
    data: ProductModelCreate,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> ProductModel:
    """Create a product model owned by the current manufacturer."""

    category = db.scalar(
        select(ProductCategory).where(
            ProductCategory.id == data.category_id,
            ProductCategory.is_active.is_(True),
        ),
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category not found",
        )

    # One query verifies template status, category, and organization ownership.
    template = db.scalar(
        select(PassportTemplate).where(
            PassportTemplate.id == data.template_id,
            PassportTemplate.organization_id == current_user.organization_id,
            PassportTemplate.category_id == data.category_id,
            PassportTemplate.status == "active",
        ),
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active passport template not found",
        )

    product_model = ProductModel(
        organization_id=current_user.organization_id,
        category_id=data.category_id,
        template_id=data.template_id,
        model_code=data.model_code,
        name=data.name,
        description=data.description,
    )
    db.add(product_model)
    commit_or_conflict(
        db,
        "A product model with this code already exists",
    )
    db.refresh(product_model)
    return product_model


@router.get("", response_model=list[ProductModelResponse])
def list_product_models(
    db: DatabaseSession,
    current_user: Manufacturer,
) -> list[ProductModel]:
    """List only product models owned by the current manufacturer."""

    statement = (
        select(ProductModel)
        .where(ProductModel.organization_id == current_user.organization_id)
        .order_by(ProductModel.created_at.desc(), ProductModel.name)
    )
    return list(db.scalars(statement).all())


@router.get("/{model_id}", response_model=ProductModelResponse)
def get_product_model(
    model_id: UUID,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> ProductModel:
    """Return one product model owned by the current manufacturer."""

    return get_owned_product_model(
        db,
        model_id,
        current_user.organization_id,
    )


@router.put("/{model_id}", response_model=ProductModelResponse)
def update_product_model(
    model_id: UUID,
    data: ProductModelUpdate,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> ProductModel:
    """Update an owned product model's name, description, or status."""

    product_model = get_owned_product_model(
        db,
        model_id,
        current_user.organization_id,
    )

    # exclude_unset distinguishes an omitted description from an explicit null.
    for attribute, value in data.model_dump(exclude_unset=True).items():
        setattr(product_model, attribute, value)

    db.commit()
    db.refresh(product_model)
    return product_model


def get_owned_product_model(
    db: Session,
    model_id: UUID,
    organization_id: UUID | None,
) -> ProductModel:
    """Load a product model only when the current organization owns it."""

    product_model = db.scalar(
        select(ProductModel).where(
            ProductModel.id == model_id,
            ProductModel.organization_id == organization_id,
        ),
    )
    if product_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product model not found",
        )
    return product_model


def commit_or_conflict(db: Session, detail: str) -> None:
    """Commit a write and return a safe message for unique-code conflicts."""

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from error
