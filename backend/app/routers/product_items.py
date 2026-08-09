from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_manufacturer
from app.models import (
    PassportTemplate,
    ProductItem,
    ProductModel,
    TemplateField,
    User,
)
from app.passport_validation import validate_passport_data
from app.qr_codes import create_qr_code_svg
from app.schemas.product_item import (
    ProductItemCreate,
    ProductItemListItem,
    ProductItemPage,
    ProductItemResponse,
    ProductItemStatus,
    ProductItemUpdate,
)


router = APIRouter(prefix="/api/product-items", tags=["product items"])

DatabaseSession = Annotated[Session, Depends(get_db)]
Manufacturer = Annotated[User, Depends(require_manufacturer)]


@router.post(
    "",
    response_model=ProductItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_item(
    data: ProductItemCreate,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> ProductItem:
    """Register one physical product as a draft passport."""

    product_model = get_owned_product_model_with_template(
        db,
        data.model_id,
        current_user.organization_id,
    )
    if (
        product_model.status != "active"
        or product_model.template.status != "active"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product items require an active model and template",
        )

    validate_data_or_422(
        data.passport_data,
        product_model.template.fields,
        require_complete=False,
    )

    product_item = ProductItem(
        organization_id=current_user.organization_id,
        model_id=product_model.id,
        serial_number=data.serial_number,
        manufacture_date=data.manufacture_date,
        passport_data=data.passport_data,
        status="draft",
    )
    db.add(product_item)
    commit_or_conflict(
        db,
        "A product item with this serial number already exists",
    )
    db.refresh(product_item)
    return product_item


@router.get("", response_model=ProductItemPage)
def list_product_items(
    db: DatabaseSession,
    current_user: Manufacturer,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    item_status: ProductItemStatus | None = Query(default=None, alias="status"),
    manufactured_from: date | None = None,
    manufactured_to: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductItemPage:
    """Search and paginate product items without loading passport JSON."""

    if (
        manufactured_from is not None
        and manufactured_to is not None
        and manufactured_from > manufactured_to
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="manufactured_from cannot be later than manufactured_to",
        )

    filters = [ProductItem.organization_id == current_user.organization_id]
    if search is not None:
        value = search.strip().lower()
        filters.append(
            or_(
                func.lower(ProductItem.serial_number).contains(
                    value,
                    autoescape=True,
                ),
                func.lower(ProductModel.name).contains(value, autoescape=True),
                cast(ProductItem.public_id, String).contains(
                    value,
                    autoescape=True,
                ),
            ),
        )
    if item_status is not None:
        filters.append(ProductItem.status == item_status)
    if manufactured_from is not None:
        filters.append(ProductItem.manufacture_date >= manufactured_from)
    if manufactured_to is not None:
        filters.append(ProductItem.manufacture_date <= manufactured_to)

    base_statement = (
        select(ProductItem, ProductModel.name.label("model_name"))
        .join(ProductModel, ProductItem.model_id == ProductModel.id)
        .where(*filters)
    )
    total = db.scalar(
        select(func.count()).select_from(base_statement.subquery()),
    ) or 0
    rows = db.execute(
        base_statement
        .order_by(ProductItem.created_at.desc(), ProductItem.serial_number)
        .offset((page - 1) * page_size)
        .limit(page_size),
    ).all()

    return ProductItemPage(
        items=[
            ProductItemListItem(
                id=item.id,
                model_id=item.model_id,
                model_name=model_name,
                serial_number=item.serial_number,
                public_id=item.public_id,
                manufacture_date=item.manufacture_date,
                status=item.status,
                created_at=item.created_at,
            )
            for item, model_name in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{item_id}", response_model=ProductItemResponse)
def get_product_item(
    item_id: UUID,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> ProductItem:
    """Return one product item owned by the current manufacturer."""

    return get_owned_product_item(
        db,
        item_id,
        current_user.organization_id,
    )


@router.get(
    "/{item_id}/qr-code",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {
            "content": {"image/svg+xml": {}},
            "description": "Printable SVG QR code",
        },
    },
)
def get_product_item_qr_code(
    item_id: UUID,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> Response:
    """Generate a printable QR code for an owned published product item."""

    product_item = get_owned_product_item(
        db,
        item_id,
        current_user.organization_id,
    )
    if product_item.status != "published":
        raise item_state_error(
            "Only published product items can have a QR code",
        )

    public_url = f"{settings.frontend_origin}/passport/{product_item.public_id}"
    svg = create_qr_code_svg(public_url)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="passport-{product_item.public_id}.svg"'
            ),
            "Cache-Control": "no-store",
        },
    )


@router.put("/{item_id}", response_model=ProductItemResponse)
def update_product_item(
    item_id: UUID,
    data: ProductItemUpdate,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> ProductItem:
    """Edit a draft, publish it, or retire a published product item."""

    product_item = get_owned_product_item(
        db,
        item_id,
        current_user.organization_id,
        load_template=True,
    )
    changes = data.model_dump(exclude_unset=True)

    if product_item.status == "retired":
        raise item_state_error("Retired product items cannot be changed")

    if product_item.status == "published":
        if set(changes) != {"status"} or data.status != "retired":
            raise item_state_error(
                "Published product items can only be retired",
            )
        product_item.status = "retired"
    else:
        passport_data = changes.get(
            "passport_data",
            product_item.passport_data,
        )
        require_complete = data.status == "published"
        validate_data_or_422(
            passport_data,
            product_item.product_model.template.fields,
            require_complete=require_complete,
        )

        for attribute, value in changes.items():
            setattr(product_item, attribute, value)

    commit_or_conflict(
        db,
        "A product item with this serial number already exists",
    )
    db.refresh(product_item)
    return product_item


def get_owned_product_model_with_template(
    db: Session,
    model_id: UUID,
    organization_id: UUID | None,
) -> ProductModel:
    """Load an owned model together with its exact template fields."""

    product_model = db.scalar(
        select(ProductModel)
        .options(
            joinedload(ProductModel.template).selectinload(
                PassportTemplate.fields,
            ),
        )
        .where(
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


def get_owned_product_item(
    db: Session,
    item_id: UUID,
    organization_id: UUID | None,
    *,
    load_template: bool = False,
) -> ProductItem:
    """Load a product item only when the current organization owns it."""

    statement = select(ProductItem).where(
        ProductItem.id == item_id,
        ProductItem.organization_id == organization_id,
    )
    if load_template:
        statement = statement.options(
            joinedload(ProductItem.product_model)
            .joinedload(ProductModel.template)
            .selectinload(PassportTemplate.fields),
        )

    product_item = db.scalar(statement)
    if product_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product item not found",
        )
    return product_item


def validate_data_or_422(
    passport_data: dict[str, object],
    fields: list[TemplateField],
    *,
    require_complete: bool,
) -> None:
    """Convert template validation failures into an API response."""

    try:
        validate_passport_data(
            passport_data,
            fields,
            require_complete=require_complete,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


def item_state_error(detail: str) -> HTTPException:
    """Create an error for a disallowed product-item lifecycle change."""

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def commit_or_conflict(db: Session, detail: str) -> None:
    """Commit a write and return a safe message for serial conflicts."""

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from error
