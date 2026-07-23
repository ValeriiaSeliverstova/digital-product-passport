from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Organization,
    PassportTemplate,
    ProductCategory,
    Role,
    TemplateField,
)
from app.schemas.template_field import TemplateFieldCreate


ROLE_NAMES = ("system_admin", "manufacturer_user")
ORGANIZATION_NAME = "KhersonSafe Ltd."
LEGACY_ORGANIZATION_NAME = "KersonSafe Ltd."
TEMPLATE_NAME = "KhersonSafe Standard Passport"

TEMPLATE_FIELDS: tuple[dict[str, Any], ...] = (
    {
        "code": "security_grade",
        "label": "Security grade",
        "data_type": "text",
        "is_required": True,
        "display_order": 1,
        "access_level": "public",
        "validation_rules": {
            "allowed_values": ["Grade 0", "Grade I", "Grade II", "Grade III"],
        },
    },
    {
        "code": "lock_type",
        "label": "Lock type",
        "data_type": "text",
        "is_required": True,
        "display_order": 2,
        "access_level": "public",
        "validation_rules": {
            "allowed_values": ["Mechanical", "Electronic"],
        },
    },
    {
        "code": "height_mm",
        "label": "Height (mm)",
        "data_type": "integer",
        "is_required": True,
        "display_order": 3,
        "access_level": "public",
        "validation_rules": {"min": 1, "max": 5000},
    },
    {
        "code": "width_mm",
        "label": "Width (mm)",
        "data_type": "integer",
        "is_required": True,
        "display_order": 4,
        "access_level": "public",
        "validation_rules": {"min": 1, "max": 5000},
    },
    {
        "code": "depth_mm",
        "label": "Depth (mm)",
        "data_type": "integer",
        "is_required": True,
        "display_order": 5,
        "access_level": "public",
        "validation_rules": {"min": 1, "max": 5000},
    },
    {
        "code": "weight_kg",
        "label": "Weight (kg)",
        "data_type": "decimal",
        "is_required": True,
        "display_order": 6,
        "access_level": "public",
        "validation_rules": {"min": 0, "max": 5000},
    },
    {
        "code": "fire_resistance_minutes",
        "label": "Fire resistance (minutes)",
        "data_type": "integer",
        "is_required": False,
        "display_order": 7,
        "access_level": "public",
        "validation_rules": {"min": 0, "max": 240},
    },
    {
        "code": "material",
        "label": "Primary material",
        "data_type": "text",
        "is_required": False,
        "display_order": 8,
        "access_level": "public",
        "validation_rules": {"max_length": 100},
    },
)


def seed_reference_data(db: Session) -> None:
    """Create the fixed roles, organization, and category hierarchy."""

    for role_name in ROLE_NAMES:
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            db.add(Role(name=role_name))

    organization = db.scalar(
        select(Organization).where(Organization.name == ORGANIZATION_NAME),
    )
    if organization is None:
        # Rename the earlier misspelled seed without changing its ID or user
        # relationships in databases where the seed has already been run.
        organization = db.scalar(
            select(Organization).where(
                Organization.name == LEGACY_ORGANIZATION_NAME,
            ),
        )
        if organization is None:
            organization = Organization(name=ORGANIZATION_NAME)
            db.add(organization)
        else:
            organization.name = ORGANIZATION_NAME

    industrial_products = upsert_category(
        db,
        code="INDUSTRIAL_PRODUCTS",
        name="Industrial Products",
    )
    security_equipment = upsert_category(
        db,
        code="SECURITY_EQUIPMENT",
        name="Security Equipment",
        parent=industrial_products,
    )
    safes = upsert_category(
        db,
        code="SAFES",
        name="Safes",
        parent=security_equipment,
    )
    upsert_category(
        db,
        code="VAULT_DOORS",
        name="Vault Doors",
        parent=security_equipment,
    )
    upsert_category(
        db,
        code="DEPOSIT_BOXES",
        name="Deposit Boxes",
        parent=security_equipment,
    )

    upsert_passport_template(db, organization=organization, category=safes)


def upsert_category(
    db: Session,
    *,
    code: str,
    name: str,
    parent: ProductCategory | None = None,
) -> ProductCategory:
    """Create a category or restore its documented seed values."""

    category = db.scalar(
        select(ProductCategory).where(ProductCategory.code == code),
    )

    if category is None:
        category = ProductCategory(code=code, name=name)
        db.add(category)

    category.name = name
    category.parent = parent
    category.is_active = True
    db.flush()
    return category


def upsert_passport_template(
    db: Session,
    *,
    organization: Organization,
    category: ProductCategory,
) -> PassportTemplate:
    """Create or restore the documented KhersonSafe template and fields."""

    template = db.scalar(
        select(PassportTemplate).where(
            PassportTemplate.organization_id == organization.id,
            PassportTemplate.category_id == category.id,
            PassportTemplate.name == TEMPLATE_NAME,
            PassportTemplate.version == 1,
        ),
    )
    if template is None:
        template = PassportTemplate(
            organization=organization,
            category=category,
            name=TEMPLATE_NAME,
            version=1,
        )
        db.add(template)
        db.flush()

    for field_data in TEMPLATE_FIELDS:
        upsert_template_field(db, template=template, field_data=field_data)

    template.status = "active"
    db.flush()
    return template


def upsert_template_field(
    db: Session,
    *,
    template: PassportTemplate,
    field_data: dict[str, Any],
) -> TemplateField:
    """Create or restore one known field without deleting custom fields."""

    validated_data = TemplateFieldCreate.model_validate(field_data).model_dump()
    field = db.scalar(
        select(TemplateField).where(
            TemplateField.template_id == template.id,
            TemplateField.code == validated_data["code"],
        ),
    )
    if field is None:
        field = TemplateField(template=template, **validated_data)
        db.add(field)
    else:
        for attribute, value in validated_data.items():
            setattr(field, attribute, value)

    db.flush()
    return field


def main() -> None:
    """Seed all reference data in one database transaction."""

    with SessionLocal.begin() as db:
        seed_reference_data(db)

    print("Reference data seeded successfully.")


if __name__ == "__main__":
    main()
