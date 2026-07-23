from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies.auth import require_manufacturer, require_system_admin
from app.models import Role, User


def build_user(role_name: str, *, has_organization: bool = False) -> User:
    """Build a user object for role-dependency unit tests."""

    return User(
        email=f"{role_name}@example.com",
        password_hash="not-used-by-authorization-tests",
        status="active",
        role=Role(name=role_name),
        organization_id=uuid4() if has_organization else None,
    )


def test_require_manufacturer_accepts_manufacturer_with_organization() -> None:
    user = build_user("manufacturer_user", has_organization=True)

    assert require_manufacturer(user) is user


def test_require_manufacturer_rejects_system_admin() -> None:
    user = build_user("system_admin")

    with pytest.raises(HTTPException) as error:
        require_manufacturer(user)

    assert error.value.status_code == 403
    assert error.value.detail == "Insufficient permissions"


def test_require_manufacturer_rejects_missing_organization() -> None:
    user = build_user("manufacturer_user")

    with pytest.raises(HTTPException) as error:
        require_manufacturer(user)

    assert error.value.status_code == 403


def test_require_system_admin_accepts_system_admin() -> None:
    user = build_user("system_admin")

    assert require_system_admin(user) is user


def test_require_system_admin_rejects_manufacturer() -> None:
    user = build_user("manufacturer_user", has_organization=True)

    with pytest.raises(HTTPException) as error:
        require_system_admin(user)

    assert error.value.status_code == 403
    assert error.value.detail == "Insufficient permissions"
