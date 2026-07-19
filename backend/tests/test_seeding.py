import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Organization, ProductCategory, Role, User
from app.security import verify_password
from scripts.create_user import create_user
from scripts.seed_reference_data import seed_reference_data


def test_reference_seed_is_idempotent(db_session: Session) -> None:
    seed_reference_data(db_session)
    seed_reference_data(db_session)
    db_session.commit()

    role_count = db_session.scalar(select(func.count()).select_from(Role))
    organization_count = db_session.scalar(
        select(func.count()).select_from(Organization),
    )
    category_count = db_session.scalar(
        select(func.count()).select_from(ProductCategory),
    )

    assert role_count == 2
    assert organization_count == 1
    assert category_count == 5

    safes = db_session.scalar(
        select(ProductCategory).where(ProductCategory.code == "SAFES"),
    )
    assert safes is not None
    assert safes.parent is not None
    assert safes.parent.code == "SECURITY_EQUIPMENT"


def test_create_manufacturer_user_hashes_password(db_session: Session) -> None:
    seed_reference_data(db_session)
    password = "a-long-development-passphrase"

    user = create_user(
        db_session,
        email="  Manufacturer@Example.com ",
        password=password,
        role_name="manufacturer_user",
        organization_name="KhersonSafe Ltd.",
    )
    db_session.commit()

    assert user.email == "manufacturer@example.com"
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)
    assert user.role.name == "manufacturer_user"
    assert user.organization is not None
    assert user.organization.name == "KhersonSafe Ltd."


def test_create_user_does_not_overwrite_existing_account(
    db_session: Session,
) -> None:
    seed_reference_data(db_session)
    create_user(
        db_session,
        email="manufacturer@example.com",
        password="first-secure-passphrase",
        role_name="manufacturer_user",
        organization_name="KhersonSafe Ltd.",
    )

    with pytest.raises(ValueError, match="already exists"):
        create_user(
            db_session,
            email="manufacturer@example.com",
            password="replacement-passphrase",
            role_name="manufacturer_user",
            organization_name="KhersonSafe Ltd.",
        )
