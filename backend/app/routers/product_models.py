from typing import Annotated
from datetime import datetime, timezone
from uuid import UUID

from cloudinary.exceptions import Error as CloudinaryError
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import (
    SERVICE_TECHNICIAN_ROLE,
    require_manufacturer,
    require_product_item_member,
)
from app.image_storage import (
    MAX_IMAGE_BYTES,
    delete_image,
    detect_image_content_type,
    upload_image,
)
from app.models import PassportTemplate, ProductCategory, ProductModel, User
from app.schemas.product_model import (
    ProductModelCreate,
    ProductModelListItem,
    ProductModelPage,
    ProductModelResponse,
    ProductModelStatus,
    ProductModelUpdate,
)


router = APIRouter(prefix="/api/product-models", tags=["product models"])

DatabaseSession = Annotated[Session, Depends(get_db)]
Manufacturer = Annotated[User, Depends(require_manufacturer)]
ProductItemMember = Annotated[User, Depends(require_product_item_member)]


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
    current_user: ProductItemMember,
) -> list[ProductModel]:
    """List only product models owned by the current manufacturer."""

    filters = [ProductModel.organization_id == current_user.organization_id]
    if current_user.role.name == SERVICE_TECHNICIAN_ROLE:
        filters.extend(
            [
                ProductModel.status == "active",
                PassportTemplate.status == "active",
            ],
        )
    statement = select(ProductModel).where(*filters)
    if current_user.role.name == SERVICE_TECHNICIAN_ROLE:
        statement = statement.join(PassportTemplate)
    statement = statement.order_by(
        ProductModel.created_at.desc(),
        ProductModel.name,
    )
    return list(db.scalars(statement).all())


@router.get("/page", response_model=ProductModelPage)
def list_product_model_page(
    db: DatabaseSession,
    current_user: Manufacturer,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    category_id: UUID | None = None,
    model_status: ProductModelStatus | None = Query(default=None, alias="status"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductModelPage:
    """Filter and paginate product-model cards for the current manufacturer."""

    filters = [ProductModel.organization_id == current_user.organization_id]
    if search is not None:
        value = search.strip().lower()
        filters.append(
            or_(
                func.lower(ProductModel.name).contains(value, autoescape=True),
                func.lower(ProductModel.model_code).contains(
                    value,
                    autoescape=True,
                ),
            ),
        )
    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if model_status is not None:
        filters.append(ProductModel.status == model_status)

    total = db.scalar(
        select(func.count(ProductModel.id)).where(*filters),
    ) or 0
    rows = db.execute(
        select(
            ProductModel,
            ProductCategory.name.label("category_name"),
            PassportTemplate.name.label("template_name"),
            PassportTemplate.version.label("template_version"),
        )
        .join(ProductCategory, ProductModel.category_id == ProductCategory.id)
        .join(PassportTemplate, ProductModel.template_id == PassportTemplate.id)
        .where(*filters)
        .order_by(ProductModel.created_at.desc(), ProductModel.name)
        .offset((page - 1) * page_size)
        .limit(page_size),
    ).all()

    return ProductModelPage(
        items=[
            ProductModelListItem(
                **ProductModelResponse.model_validate(model).model_dump(),
                category_name=category_name,
                template_name=template_name,
                template_version=template_version,
            )
            for model, category_name, template_name, template_version in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{model_id}", response_model=ProductModelResponse)
def get_product_model(
    model_id: UUID,
    db: DatabaseSession,
    current_user: ProductItemMember,
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


@router.put("/{model_id}/image", response_model=ProductModelResponse)
def upload_product_model_image(
    model_id: UUID,
    db: DatabaseSession,
    current_user: Manufacturer,
    image: Annotated[UploadFile, File()],
) -> ProductModel:
    """Upload or replace an owned product model's public image."""

    image_data = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(image_data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Product model image must not exceed 2 MB",
        )
    if detect_image_content_type(image_data) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Product model image must be a PNG, JPEG, or WebP image",
        )

    product_model = get_owned_product_model(
        db,
        model_id,
        current_user.organization_id,
    )
    try:
        public_id, image_url = upload_image(
            image_data,
            folder="digital-product-passport/product-models",
            public_id=str(product_model.id),
        )
    except (CloudinaryError, RuntimeError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Product model image could not be uploaded",
        ) from error

    product_model.image_public_id = public_id
    product_model.image_url = image_url
    product_model.image_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(product_model)
    return product_model


@router.delete("/{model_id}/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_model_image(
    model_id: UUID,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> Response:
    """Delete an owned product model's image from Cloudinary."""

    product_model = get_owned_product_model(
        db,
        model_id,
        current_user.organization_id,
    )
    if product_model.image_public_id is not None:
        try:
            delete_image(product_model.image_public_id)
        except (CloudinaryError, RuntimeError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Product model image could not be deleted",
            ) from error

    product_model.image_public_id = None
    product_model.image_url = None
    product_model.image_updated_at = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{model_id}/image", response_class=RedirectResponse)
def get_product_model_image(
    model_id: UUID,
    db: DatabaseSession,
) -> RedirectResponse:
    """Redirect public image requests to Cloudinary's delivery CDN."""

    product_model = db.get(ProductModel, model_id)
    if product_model is None or product_model.image_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product model image not found",
        )
    return RedirectResponse(
        url=product_model.image_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Cache-Control": "public, max-age=3600"},
    )


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
