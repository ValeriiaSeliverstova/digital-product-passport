from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from app.models import Organization, Role, User
from app.security import create_access_token, hash_password


def create_user(
    db: Session,
    *,
    role_name: str,
    organization: Organization | None = None,
) -> User:
    """Create an authenticated user for organization endpoint tests."""

    user = User(
        email=f"{role_name}@example.com",
        password_hash=hash_password("test-password-at-least-12-characters"),
        status="active",
        role=Role(name=role_name),
        organization=organization,
    )
    db.add(user)
    db.commit()
    return user


def authorization_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def test_manufacturer_can_update_own_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = Organization(name="Original Organization")
    other_organization = Organization(name="Other Organization")
    db_session.add(other_organization)
    user = create_user(
        db_session,
        role_name="manufacturer_user",
        organization=organization,
    )

    response = client.put(
        "/api/organizations/me",
        headers=authorization_header(user),
        json={
            "name": "  Updated Safety Institute  ",
            "country": "Ukraine",
            "address_line_1": "10 Example Street",
            "address_line_2": "Building B",
            "city": "Kherson",
            "postal_code": "73000",
            "contact_email": "CONTACT@EXAMPLE.COM",
            "phone": "+380 00 000 00 00",
            "website": "https://example.com/manufacturer",
            "azure_devops_area_path": "Students\\Safety Institute",
            "azure_devops_work_item_type": "Customer Support",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(organization.id),
        "name": "Updated Safety Institute",
        "country": "Ukraine",
        "address_line_1": "10 Example Street",
        "address_line_2": "Building B",
        "city": "Kherson",
        "postal_code": "73000",
        "contact_email": "contact@example.com",
        "phone": "+380 00 000 00 00",
        "website": "https://example.com/manufacturer",
        "azure_devops_area_path": "Students\\Safety Institute",
        "azure_devops_work_item_type": "Customer Support",
        "has_logo": False,
        "logo_updated_at": None,
    }
    db_session.refresh(organization)
    db_session.refresh(other_organization)
    assert organization.name == "Updated Safety Institute"
    assert organization.country == "Ukraine"
    assert organization.contact_email == "contact@example.com"
    assert organization.azure_devops_area_path == "Students\\Safety Institute"
    assert other_organization.name == "Other Organization"


def test_manufacturer_can_upload_view_and_delete_logo(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    organization = Organization(name="Logo Organization")
    user = create_user(
        db_session,
        role_name="manufacturer_user",
        organization=organization,
    )
    headers = authorization_header(user)
    png_data = b"\x89PNG\r\n\x1a\n" + b"test-image-data"
    deleted_public_ids: list[str] = []
    monkeypatch.setattr(
        "app.routers.organizations.upload_image",
        lambda *_args, **_kwargs: (
            f"digital-product-passport/organizations/{organization.id}",
            "https://res.cloudinary.com/example/image/upload/logo.png",
        ),
    )
    monkeypatch.setattr(
        "app.routers.organizations.delete_image",
        deleted_public_ids.append,
    )

    upload = client.put(
        "/api/organizations/me/logo",
        headers=headers,
        files={"logo": ("logo.png", png_data, "image/png")},
    )

    assert upload.status_code == 200, upload.text
    assert upload.json()["has_logo"] is True
    assert upload.json()["logo_updated_at"] is not None

    image = client.get(
        f"/api/organizations/{organization.id}/logo",
        follow_redirects=False,
    )
    assert image.status_code == 307
    assert image.headers["location"] == (
        "https://res.cloudinary.com/example/image/upload/logo.png"
    )

    delete = client.delete("/api/organizations/me/logo", headers=headers)
    assert delete.status_code == 204
    assert deleted_public_ids == [
        f"digital-product-passport/organizations/{organization.id}",
    ]
    assert client.get(f"/api/organizations/{organization.id}/logo").status_code == 404


def test_logo_upload_validates_image_type_and_size(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_user(
        db_session,
        role_name="manufacturer_user",
        organization=Organization(name="Logo Organization"),
    )
    headers = authorization_header(user)

    invalid_type = client.put(
        "/api/organizations/me/logo",
        headers=headers,
        files={"logo": ("logo.svg", b"<svg></svg>", "image/svg+xml")},
    )
    too_large = client.put(
        "/api/organizations/me/logo",
        headers=headers,
        files={
            "logo": (
                "logo.png",
                b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024),
                "image/png",
            ),
        },
    )

    assert invalid_type.status_code == 422
    assert too_large.status_code == 413


def test_organization_update_rejects_system_admin(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_user(db_session, role_name="system_admin")

    response = client.put(
        "/api/organizations/me",
        headers=authorization_header(user),
        json={"name": "Not Allowed"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_organization_update_validates_name(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_user(
        db_session,
        role_name="manufacturer_user",
        organization=Organization(name="Original Organization"),
    )

    blank_response = client.put(
        "/api/organizations/me",
        headers=authorization_header(user),
        json={"name": "   "},
    )
    long_response = client.put(
        "/api/organizations/me",
        headers=authorization_header(user),
        json={"name": "x" * 256},
    )

    assert blank_response.status_code == 422
    assert long_response.status_code == 422


def test_organization_update_validates_contact_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_user(
        db_session,
        role_name="manufacturer_user",
        organization=Organization(name="Original Organization"),
    )
    headers = authorization_header(user)

    invalid_email = client.put(
        "/api/organizations/me",
        headers=headers,
        json={"name": "Original Organization", "contact_email": "invalid"},
    )
    invalid_website = client.put(
        "/api/organizations/me",
        headers=headers,
        json={"name": "Original Organization", "website": "example.com"},
    )

    assert invalid_email.status_code == 422
    assert invalid_website.status_code == 422


def test_organization_update_preserves_omitted_optional_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    organization = Organization(
        name="Original Organization",
        country="Ukraine",
        city="Kherson",
    )
    user = create_user(
        db_session,
        role_name="manufacturer_user",
        organization=organization,
    )

    response = client.put(
        "/api/organizations/me",
        headers=authorization_header(user),
        json={"name": "Renamed Organization"},
    )

    assert response.status_code == 200
    assert response.json()["country"] == "Ukraine"
    assert response.json()["city"] == "Kherson"
