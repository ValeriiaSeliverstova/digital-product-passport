from copy import deepcopy
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies.auth import require_manufacturer
from app.models import PassportTemplate, ProductCategory, TemplateField, User
from app.schemas.passport_template import (
    PassportTemplateCreate,
    PassportTemplateDetailResponse,
    PassportTemplateResponse,
    PassportTemplateUpdate,
)
from app.schemas.template_field import (
    TemplateFieldCreateList,
    TemplateFieldResponse,
    TemplateFieldUpdate,
)


router = APIRouter(prefix="/api/templates", tags=["passport templates"])

DatabaseSession = Annotated[Session, Depends(get_db)]
Manufacturer = Annotated[User, Depends(require_manufacturer)]


@router.post(
    "",
    response_model=PassportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    data: PassportTemplateCreate,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> PassportTemplate:
    """Create a draft template owned by the current manufacturer."""

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

    template = PassportTemplate(
        organization_id=current_user.organization_id,
        category_id=data.category_id,
        name=data.name,
        version=data.version,
        status="draft",
    )
    db.add(template)
    commit_or_conflict(db, "This template version already exists")
    db.refresh(template)
    return template


@router.get("", response_model=list[PassportTemplateResponse])
def list_templates(
    db: DatabaseSession,
    current_user: Manufacturer,
) -> list[PassportTemplate]:
    """List only templates owned by the current manufacturer."""

    statement = (
        select(PassportTemplate)
        .where(
            PassportTemplate.organization_id == current_user.organization_id,
        )
        .order_by(PassportTemplate.created_at.desc(), PassportTemplate.name)
    )
    return list(db.scalars(statement).all())


@router.get(
    "/{template_id}",
    response_model=PassportTemplateDetailResponse,
)
def get_template(
    template_id: UUID,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> PassportTemplate:
    """Return one owned template and its ordered fields."""

    return get_owned_template(
        db,
        template_id,
        current_user.organization_id,
        load_fields=True,
    )


@router.put("/{template_id}", response_model=PassportTemplateResponse)
def update_template(
    template_id: UUID,
    data: PassportTemplateUpdate,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> PassportTemplate:
    """Rename a template family or move one version through its lifecycle."""

    template = get_owned_template(
        db,
        template_id,
        current_user.organization_id,
        load_fields=True,
    )

    if template.status == "archived" and data.status is not None:
        raise template_state_error("Archived template status cannot be changed")

    if template.status == "active":
        if data.status not in {None, "archived"}:
            raise template_state_error(
                "Active templates cannot return to draft",
            )
        if data.status == "archived":
            template.status = "archived"
    elif template.status == "draft":
        if data.status == "active" and not template.fields:
            raise template_state_error(
                "A template needs at least one field before activation",
            )
        if data.status is not None:
            template.status = data.status

    if data.name is not None:
        # A name describes the family, so keep it consistent across versions.
        db.execute(
            update(PassportTemplate)
            .where(
                PassportTemplate.template_family_id
                == template.template_family_id,
            )
            .values(name=data.name),
        )
        template.name = data.name

    commit_or_conflict(db, "This template version already exists")
    db.refresh(template)
    return template


@router.post(
    "/{template_id}/versions",
    response_model=PassportTemplateDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template_version(
    template_id: UUID,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> PassportTemplate:
    """Copy an active or archived template into the next draft version."""

    source = get_owned_template(
        db,
        template_id,
        current_user.organization_id,
        load_fields=True,
    )
    if source.status == "draft":
        raise template_state_error(
            "Edit the existing draft instead of creating another version",
        )

    existing_draft = db.scalar(
        select(PassportTemplate.id).where(
            PassportTemplate.template_family_id == source.template_family_id,
            PassportTemplate.status == "draft",
        ),
    )
    if existing_draft is not None:
        raise template_state_error(
            "Finish the existing draft before creating another version",
        )

    latest_version = db.scalar(
        select(func.max(PassportTemplate.version)).where(
            PassportTemplate.template_family_id == source.template_family_id,
        ),
    )
    if latest_version is not None and source.version != latest_version:
        raise template_state_error(
            "Create a new version from the latest template version",
        )
    next_version = (latest_version or source.version) + 1

    new_template = PassportTemplate(
        template_family_id=source.template_family_id,
        organization_id=source.organization_id,
        category_id=source.category_id,
        name=source.name,
        version=next_version,
        status="draft",
        fields=[
            TemplateField(
                code=field.code,
                label=field.label,
                data_type=field.data_type,
                is_required=field.is_required,
                display_order=field.display_order,
                access_level=field.access_level,
                validation_rules=deepcopy(field.validation_rules),
            )
            for field in source.fields
        ],
    )
    db.add(new_template)
    commit_or_conflict(db, "The next template version already exists")
    db.refresh(new_template)
    return new_template


@router.post(
    "/{template_id}/fields",
    response_model=list[TemplateFieldResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_template_fields(
    template_id: UUID,
    data: TemplateFieldCreateList,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> list[TemplateField]:
    """Add one or more validated fields to an owned draft template."""

    template = get_owned_template(
        db,
        template_id,
        current_user.organization_id,
    )
    require_draft_template(template)

    fields = [
        TemplateField(template_id=template.id, **item.model_dump())
        for item in data
    ]
    db.add_all(fields)
    commit_or_conflict(db, "A field with this code already exists")
    for field in fields:
        db.refresh(field)
    # Keep the loaded template in sync for later lifecycle checks.
    db.refresh(template, attribute_names=["fields"])
    return fields


@router.put(
    "/{template_id}/fields/{field_id}",
    response_model=TemplateFieldResponse,
)
def update_template_field(
    template_id: UUID,
    field_id: UUID,
    data: TemplateFieldUpdate,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> TemplateField:
    """Replace an existing field definition on an owned draft template."""

    template = get_owned_template(
        db,
        template_id,
        current_user.organization_id,
    )
    require_draft_template(template)
    field = get_template_field(db, template.id, field_id)

    for attribute, value in data.model_dump().items():
        setattr(field, attribute, value)

    commit_or_conflict(db, "A field with this code already exists")
    db.refresh(field)
    return field


@router.delete(
    "/{template_id}/fields/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_template_field(
    template_id: UUID,
    field_id: UUID,
    db: DatabaseSession,
    current_user: Manufacturer,
) -> Response:
    """Remove a field from an owned draft template."""

    template = get_owned_template(
        db,
        template_id,
        current_user.organization_id,
    )
    require_draft_template(template)
    field = get_template_field(db, template.id, field_id)

    db.delete(field)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def get_owned_template(
    db: Session,
    template_id: UUID,
    organization_id: UUID | None,
    *,
    load_fields: bool = False,
) -> PassportTemplate:
    """Load a template only when it belongs to the current organization."""

    statement = select(PassportTemplate).where(
        PassportTemplate.id == template_id,
        PassportTemplate.organization_id == organization_id,
    )
    if load_fields:
        statement = statement.options(selectinload(PassportTemplate.fields))

    template = db.scalar(statement)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passport template not found",
        )
    return template


def get_template_field(
    db: Session,
    template_id: UUID,
    field_id: UUID,
) -> TemplateField:
    """Load a field only through its already-authorized parent template."""

    field = db.scalar(
        select(TemplateField).where(
            TemplateField.id == field_id,
            TemplateField.template_id == template_id,
        ),
    )
    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template field not found",
        )
    return field


def require_draft_template(template: PassportTemplate) -> None:
    """Reject structural changes after a template leaves draft status."""

    if template.status != "draft":
        raise template_state_error("Only draft templates can change fields")


def template_state_error(detail: str) -> HTTPException:
    """Create an error for a disallowed template lifecycle operation."""

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def commit_or_conflict(db: Session, detail: str) -> None:
    """Commit a write and convert uniqueness failures to a safe API error."""

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from error
