from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Organization,
    PassportTemplate,
    ProductCategory,
    Role,
    User,
)
from app.security import create_access_token


def create_user_and_headers(
    db: Session,
    role_name: str,
    *,
    organization_name: str | None = None,
) -> tuple[User, dict[str, str]]:
    """Create a test identity and its bearer-token header."""

    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name)

    organization = None
    if organization_name is not None:
        organization = Organization(name=organization_name)

    user = User(
        email=f"{uuid4()}@example.com",
        password_hash="not-used-by-template-api-tests",
        status="active",
        role=role,
        organization=organization,
    )
    db.add(user)
    db.commit()

    token = create_access_token(user.id)
    return user, {"Authorization": f"Bearer {token}"}


def create_category(db: Session, *, active: bool = True) -> ProductCategory:
    category = ProductCategory(
        code=f"CATEGORY_{uuid4().hex}",
        name="Test Safes",
        is_active=active,
    )
    db.add(category)
    db.commit()
    return category


def create_template_through_api(
    client: TestClient,
    headers: dict[str, str],
    category: ProductCategory,
) -> dict[str, object]:
    response = client.post(
        "/api/templates",
        headers=headers,
        json={
            "category_id": str(category.id),
            "name": "Standard Safe Passport",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def valid_field_data() -> dict[str, object]:
    return {
        "code": "weight_kg",
        "label": "Weight",
        "data_type": "decimal",
        "is_required": True,
        "display_order": 2,
        "access_level": "public",
        "validation_rules": {"min": 0, "max": 2000},
    }


def test_template_creation_requires_manufacturer_role(
    client: TestClient,
    db_session: Session,
) -> None:
    category = create_category(db_session)
    _, admin_headers = create_user_and_headers(db_session, "system_admin")
    request_data = {
        "category_id": str(category.id),
        "name": "Standard Safe Passport",
    }

    unauthenticated = client.post("/api/templates", json=request_data)
    wrong_role = client.post(
        "/api/templates",
        headers=admin_headers,
        json=request_data,
    )

    assert unauthenticated.status_code == 401
    assert wrong_role.status_code == 403


def test_template_creation_uses_authenticated_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)

    template = create_template_through_api(client, headers, category)

    assert template["organization_id"] == str(user.organization_id)
    assert template["template_family_id"]
    assert template["status"] == "draft"
    assert template["version"] == 1


def test_template_queries_hide_other_organizations(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    other_user, _ = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer B",
    )
    category = create_category(db_session)

    owned = PassportTemplate(
        organization_id=user.organization_id,
        category_id=category.id,
        name="Owned Template",
    )
    other = PassportTemplate(
        organization_id=other_user.organization_id,
        category_id=category.id,
        name="Other Template",
    )
    db_session.add_all([owned, other])
    db_session.commit()

    list_response = client.get("/api/templates", headers=headers)
    other_response = client.get(
        f"/api/templates/{other.id}",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [str(owned.id)]
    assert other_response.status_code == 404


def test_template_field_crud(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)
    template = create_template_through_api(client, headers, category)
    template_id = template["id"]

    create_response = client.post(
        f"/api/templates/{template_id}/fields",
        headers=headers,
        json=[valid_field_data()],
    )
    assert create_response.status_code == 201
    field_id = create_response.json()[0]["id"]

    update_data = valid_field_data()
    update_data["label"] = "Product weight"
    update_data["display_order"] = 1
    update_response = client.put(
        f"/api/templates/{template_id}/fields/{field_id}",
        headers=headers,
        json=update_data,
    )
    assert update_response.status_code == 200
    assert update_response.json()["label"] == "Product weight"

    detail_response = client.get(
        f"/api/templates/{template_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["fields"][0]["id"] == field_id

    delete_response = client.delete(
        f"/api/templates/{template_id}/fields/{field_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    final_detail = client.get(
        f"/api/templates/{template_id}",
        headers=headers,
    )
    assert final_detail.json()["fields"] == []


def test_active_template_fields_cannot_change(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)
    template = create_template_through_api(client, headers, category)
    template_id = template["id"]

    empty_activation = client.put(
        f"/api/templates/{template_id}",
        headers=headers,
        json={"status": "active"},
    )
    assert empty_activation.status_code == 409

    field_response = client.post(
        f"/api/templates/{template_id}/fields",
        headers=headers,
        json=[valid_field_data()],
    )
    assert field_response.status_code == 201

    activation = client.put(
        f"/api/templates/{template_id}",
        headers=headers,
        json={"status": "active"},
    )
    assert activation.status_code == 200
    assert activation.json()["status"] == "active"

    additional_field = valid_field_data()
    additional_field["code"] = "height_mm"
    blocked_change = client.post(
        f"/api/templates/{template_id}/fields",
        headers=headers,
        json=[additional_field],
    )
    assert blocked_change.status_code == 409

    archive = client.put(
        f"/api/templates/{template_id}",
        headers=headers,
        json={"status": "archived"},
    )
    assert archive.status_code == 200
    assert archive.json()["status"] == "archived"


def test_active_template_can_be_copied_to_next_draft_version(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)
    source = create_template_through_api(client, headers, category)
    source_id = source["id"]

    field_response = client.post(
        f"/api/templates/{source_id}/fields",
        headers=headers,
        json=[valid_field_data()],
    )
    source_field = field_response.json()[0]
    client.put(
        f"/api/templates/{source_id}",
        headers=headers,
        json={"status": "active"},
    )
    active_rename = client.put(
        f"/api/templates/{source_id}",
        headers=headers,
        json={"name": "Updated Standard Safe Passport"},
    )
    assert active_rename.status_code == 200

    response = client.post(
        f"/api/templates/{source_id}/versions",
        headers=headers,
    )

    assert response.status_code == 201
    new_version = response.json()
    assert new_version["id"] != source_id
    assert new_version["template_family_id"] == source["template_family_id"]
    assert new_version["version"] == 2
    assert new_version["status"] == "draft"
    assert new_version["fields"][0]["id"] != source_field["id"]
    assert new_version["fields"][0]["code"] == source_field["code"]
    assert new_version["fields"][0]["validation_rules"] == {
        "min": 0,
        "max": 2000,
    }

    rename_response = client.put(
        f"/api/templates/{new_version['id']}",
        headers=headers,
        json={"name": "Renamed family"},
    )
    assert rename_response.status_code == 200
    source_after_rename = client.get(
        f"/api/templates/{source_id}",
        headers=headers,
    )
    assert source_after_rename.json()["name"] == "Renamed family"

    duplicate_draft = client.post(
        f"/api/templates/{source_id}/versions",
        headers=headers,
    )
    assert duplicate_draft.status_code == 409

    client.put(
        f"/api/templates/{new_version['id']}",
        headers=headers,
        json={"status": "active"},
    )
    old_source = client.post(
        f"/api/templates/{source_id}/versions",
        headers=headers,
    )
    assert old_source.status_code == 409
    assert old_source.json() == {
        "detail": "Create a new version from the latest template version",
    }


def test_draft_template_cannot_create_another_version(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)
    template = create_template_through_api(client, headers, category)

    response = client.post(
        f"/api/templates/{template['id']}/versions",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Edit the existing draft instead of creating another version",
    }


def test_field_validation_rejects_unsupported_rules(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)
    template = create_template_through_api(client, headers, category)
    field_data = valid_field_data()
    field_data["validation_rules"] = {"min_length": 2}

    response = client.post(
        f"/api/templates/{template['id']}/fields",
        headers=headers,
        json=[field_data],
    )

    assert response.status_code == 422


def test_multiple_template_fields_are_created_together(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)
    template = create_template_through_api(client, headers, category)

    weight = valid_field_data()
    height = valid_field_data()
    height.update(
        {
            "code": "height_mm",
            "label": "Height",
            "display_order": 3,
        },
    )

    response = client.post(
        f"/api/templates/{template['id']}/fields",
        headers=headers,
        json=[weight, height],
    )

    assert response.status_code == 201
    assert [field["code"] for field in response.json()] == [
        "weight_kg",
        "height_mm",
    ]


def test_duplicate_in_field_batch_saves_nothing(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)
    template = create_template_through_api(client, headers, category)
    duplicate = valid_field_data()

    response = client.post(
        f"/api/templates/{template['id']}/fields",
        headers=headers,
        json=[valid_field_data(), duplicate],
    )

    assert response.status_code == 409
    detail = client.get(
        f"/api/templates/{template['id']}",
        headers=headers,
    )
    assert detail.json()["fields"] == []


def test_duplicate_template_version_returns_conflict(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_user_and_headers(
        db_session,
        "manufacturer_user",
        organization_name="Manufacturer A",
    )
    category = create_category(db_session)

    create_template_through_api(client, headers, category)
    duplicate = client.post(
        "/api/templates",
        headers=headers,
        json={
            "category_id": str(category.id),
            "name": "Standard Safe Passport",
            "version": 1,
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "This template version already exists"}
