from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Organization, ProductCategory, Role


ROLE_NAMES = ("system_admin", "manufacturer_user")
ORGANIZATION_NAME = "KhersonSafe Ltd."
LEGACY_ORGANIZATION_NAME = "KersonSafe Ltd."


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
            db.add(Organization(name=ORGANIZATION_NAME))
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
    upsert_category(
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


def main() -> None:
    """Seed all reference data in one database transaction."""

    with SessionLocal.begin() as db:
        seed_reference_data(db)

    print("Reference data seeded successfully.")


if __name__ == "__main__":
    main()
