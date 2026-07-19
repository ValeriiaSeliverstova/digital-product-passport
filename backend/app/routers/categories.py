from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProductCategory
from app.schemas.product_category import ProductCategoryResponse


router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[ProductCategoryResponse])
def list_categories(db: Session = Depends(get_db)) -> list[ProductCategory]:
    """Return all active product categories ordered by name."""

    statement = (
        select(ProductCategory)
        .where(ProductCategory.is_active.is_(True))
        .order_by(ProductCategory.name)
    )

    return list(db.scalars(statement).all())


@router.get("/{category_id}", response_model=ProductCategoryResponse)
def get_category(
    category_id: UUID,
    db: Session = Depends(get_db),
) -> ProductCategory:
    """Return one active product category by its ID."""

    statement = select(ProductCategory).where(
        ProductCategory.id == category_id,
        ProductCategory.is_active.is_(True),
    )
    category = db.scalar(statement)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category not found",
        )

    return category
