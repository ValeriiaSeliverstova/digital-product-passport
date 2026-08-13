from fastapi.testclient import TestClient
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, Role, User
from app.security import create_access_token, hash_password, verify_password


def create_role(db: Session, name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name)
        db.add(role)
        db.flush()
    return role


def create_user(
    db: Session,
    *,
    role_name: str,
    organization: Organization | None,
    email: str,
) -> tuple[User, dict[str, str]]:
    user = User(
        email=email,
        password_hash=hash_password("test-password-123"),
        role=create_role(db, role_name),
        organization=organization,
        status="active",
    )
    db.add(user)
    db.commit()
    return user, {
        "Authorization": f"Bearer {create_access_token(user.id)}",
    }


def test_organization_admin_can_create_list_and_deactivate_technician(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = Organization(name="Example Manufacturer")
    db_session.add(organization)
    create_role(db_session, "service_technician")
    _, headers = create_user(
        db_session,
        role_name="manufacturer_user",
        organization=organization,
        email="admin@example.com",
    )

    created = client.post(
        "/api/organizations/me/team-members",
        headers=headers,
        json={
            "email": "Technician@Example.com",
            "initial_password": "temporary-password-123",
        },
    )

    assert created.status_code == 201, created.text
    result = created.json()
    assert result["email"] == "technician@example.com"
    assert result["status"] == "active"
    assert result["role"] == "service_technician"
    stored = db_session.get(User, UUID(result["id"]))
    assert stored is not None
    assert stored.organization_id == organization.id
    assert verify_password("temporary-password-123", stored.password_hash)

    listed = client.get("/api/organizations/me/team-members", headers=headers)
    assert listed.status_code == 200
    assert [member["id"] for member in listed.json()] == [result["id"]]

    deactivated = client.put(
        f"/api/organizations/me/team-members/{result['id']}",
        headers=headers,
        json={"status": "inactive"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"


def test_technician_cannot_manage_team_members(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = Organization(name="Example Manufacturer")
    db_session.add(organization)
    _, headers = create_user(
        db_session,
        role_name="service_technician",
        organization=organization,
        email="technician@example.com",
    )

    response = client.get("/api/organizations/me/team-members", headers=headers)

    assert response.status_code == 403


def test_admin_cannot_manage_other_organization_technician(
    client: TestClient,
    db_session: Session,
) -> None:
    first = Organization(name="First Manufacturer")
    second = Organization(name="Second Manufacturer")
    db_session.add_all([first, second])
    _, admin_headers = create_user(
        db_session,
        role_name="manufacturer_user",
        organization=first,
        email="admin@example.com",
    )
    technician, _ = create_user(
        db_session,
        role_name="service_technician",
        organization=second,
        email="technician@example.com",
    )

    response = client.put(
        f"/api/organizations/me/team-members/{technician.id}",
        headers=admin_headers,
        json={"status": "inactive"},
    )

    assert response.status_code == 404
    assert technician.status == "active"
