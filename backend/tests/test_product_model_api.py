from uuid import uuid4

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Organization,
    PassportTemplate,
    ProductCategory,
    ProductModel,
    Role,
    User,
)
from app.security import create_access_token


def create_manufacturer(
    db: Session,
    organization_name: str,
) -> tuple[User, dict[str, str]]:
    """Create a manufacturer identity for an isolated API test."""

    role = db.scalar(select(Role).where(Role.name == "manufacturer_user"))
    if role is None:
        role = Role(name="manufacturer_user")

    user = User(
        email=f"{uuid4()}@example.com",
        password_hash="not-used-by-product-model-api-tests",
        status="active",
        role=role,
        organization=Organization(name=organization_name),
    )
    db.add(user)
    db.commit()

    token = create_access_token(user.id)
    return user, {"Authorization": f"Bearer {token}"}


def create_category(
    db: Session,
    *,
    active: bool = True,
) -> ProductCategory:
    category = ProductCategory(
        code=f"CATEGORY_{uuid4().hex}",
        name="Test Safes",
        is_active=active,
    )
    db.add(category)
    db.commit()
    return category


def create_template(
    db: Session,
    user: User,
    category: ProductCategory,
    *,
    template_status: str = "active",
) -> PassportTemplate:
    template = PassportTemplate(
        organization_id=user.organization_id,
        category_id=category.id,
        name=f"Test Passport {uuid4()}",
        status=template_status,
    )
    db.add(template)
    db.commit()
    return template


def product_model_data(
    category: ProductCategory,
    template: PassportTemplate,
    *,
    model_code: str = "EDS-40",
) -> dict[str, str]:
    return {
        "category_id": str(category.id),
        "template_id": str(template.id),
        "model_code": model_code,
        "name": "EveryDaySafe 40",
        "description": "A compact safe for homes and small offices.",
    }


def test_product_model_creation_requires_manufacturer(
    client: TestClient,
    db_session: Session,
) -> None:
    user, _ = create_manufacturer(db_session, "Manufacturer A")
    category = create_category(db_session)
    template = create_template(db_session, user, category)

    response = client.post(
        "/api/product-models",
        json=product_model_data(category, template),
    )

    assert response.status_code == 401


def test_product_model_creation_uses_authenticated_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    category = create_category(db_session)
    template = create_template(db_session, user, category)

    response = client.post(
        "/api/product-models",
        headers=headers,
        json=product_model_data(category, template),
    )

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["organization_id"] == str(user.organization_id)
    assert result["template_id"] == str(template.id)
    assert result["model_code"] == "EDS-40"
    assert result["description"] == (
        "A compact safe for homes and small offices."
    )
    assert result["status"] == "active"
    assert result["has_image"] is False
    assert result["image_updated_at"] is None


def test_manufacturer_can_upload_view_and_delete_product_model_image(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    category = create_category(db_session)
    template = create_template(db_session, user, category)
    create_response = client.post(
        "/api/product-models",
        headers=headers,
        json=product_model_data(category, template),
    )
    model_id = create_response.json()["id"]
    public_id = f"digital-product-passport/product-models/{model_id}"
    image_url = "https://res.cloudinary.com/example/image/upload/model.png"
    deleted: list[str] = []
    monkeypatch.setattr(
        "app.routers.product_models.upload_image",
        lambda *_args, **_kwargs: (public_id, image_url),
    )
    monkeypatch.setattr(
        "app.routers.product_models.delete_image",
        deleted.append,
    )

    upload = client.put(
        f"/api/product-models/{model_id}/image",
        headers=headers,
        files={
            "image": (
                "model.png",
                b"\x89PNG\r\n\x1a\nmodel-image",
                "image/png",
            ),
        },
    )

    assert upload.status_code == 200, upload.text
    assert upload.json()["has_image"] is True
    assert upload.json()["image_updated_at"] is not None

    image = client.get(
        f"/api/product-models/{model_id}/image",
        follow_redirects=False,
    )
    assert image.status_code == 307
    assert image.headers["location"] == image_url

    delete = client.delete(
        f"/api/product-models/{model_id}/image",
        headers=headers,
    )
    assert delete.status_code == 204
    assert deleted == [public_id]
    assert client.get(f"/api/product-models/{model_id}/image").status_code == 404


def test_product_model_image_upload_enforces_organization_ownership(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, _ = create_manufacturer(db_session, "Manufacturer B")
    category = create_category(db_session)
    template = create_template(db_session, other_user, category)
    product_model = ProductModel(
        organization_id=other_user.organization_id,
        category_id=category.id,
        template_id=template.id,
        model_code="OTHER-IMAGE",
        name="Other Model",
    )
    db_session.add(product_model)
    db_session.commit()

    response = client.put(
        f"/api/product-models/{product_model.id}/image",
        headers=headers,
        files={
            "image": (
                "model.png",
                b"\x89PNG\r\n\x1a\nmodel-image",
                "image/png",
            ),
        },
    )

    assert response.status_code == 404


def test_product_model_requires_active_category_and_matching_active_template(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    inactive_category = create_category(db_session, active=False)
    inactive_category_template = create_template(
        db_session,
        user,
        inactive_category,
    )

    inactive_category_response = client.post(
        "/api/product-models",
        headers=headers,
        json=product_model_data(
            inactive_category,
            inactive_category_template,
        ),
    )
    assert inactive_category_response.status_code == 404

    category = create_category(db_session)
    draft_template = create_template(
        db_session,
        user,
        category,
        template_status="draft",
    )
    draft_response = client.post(
        "/api/product-models",
        headers=headers,
        json=product_model_data(category, draft_template),
    )
    assert draft_response.status_code == 404

    other_category = create_category(db_session)
    active_template = create_template(db_session, user, other_category)
    mismatched_response = client.post(
        "/api/product-models",
        headers=headers,
        json=product_model_data(category, active_template),
    )
    assert mismatched_response.status_code == 404


def test_product_model_rejects_another_organization_template(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, _ = create_manufacturer(db_session, "Manufacturer B")
    category = create_category(db_session)
    other_template = create_template(db_session, other_user, category)

    response = client.post(
        "/api/product-models",
        headers=headers,
        json=product_model_data(category, other_template),
    )

    assert response.status_code == 404


def test_product_model_queries_hide_other_organizations(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, _ = create_manufacturer(db_session, "Manufacturer B")
    category = create_category(db_session)
    template = create_template(db_session, user, category)
    other_template = create_template(db_session, other_user, category)
    owned = ProductModel(
        organization_id=user.organization_id,
        category_id=category.id,
        template_id=template.id,
        model_code="OWNED-1",
        name="Owned Model",
    )
    other = ProductModel(
        organization_id=other_user.organization_id,
        category_id=category.id,
        template_id=other_template.id,
        model_code="OTHER-1",
        name="Other Model",
    )
    db_session.add_all([owned, other])
    db_session.commit()

    list_response = client.get("/api/product-models", headers=headers)
    other_response = client.get(
        f"/api/product-models/{other.id}",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [str(owned.id)]
    assert other_response.status_code == 404


def test_product_model_page_supports_search_filters_and_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, _ = create_manufacturer(db_session, "Manufacturer B")
    safes = create_category(db_session)
    cabinets = create_category(db_session)
    safes_template = create_template(db_session, user, safes)
    cabinets_template = create_template(db_session, user, cabinets)
    other_template = create_template(db_session, other_user, safes)
    models = [
        ProductModel(
            organization_id=user.organization_id,
            category_id=safes.id,
            template_id=safes_template.id,
            model_code="HERITAGE-1920",
            name="Heritage Safe",
            status="active",
        ),
        ProductModel(
            organization_id=user.organization_id,
            category_id=safes.id,
            template_id=safes_template.id,
            model_code="MODERN-40",
            name="Modern Safe",
            status="archived",
        ),
        ProductModel(
            organization_id=user.organization_id,
            category_id=cabinets.id,
            template_id=cabinets_template.id,
            model_code="CABINET-10",
            name="Document Cabinet",
            status="active",
        ),
        ProductModel(
            organization_id=other_user.organization_id,
            category_id=safes.id,
            template_id=other_template.id,
            model_code="OTHER-40",
            name="Other Organization Model",
        ),
    ]
    db_session.add_all(models)
    db_session.commit()

    first_page = client.get(
        "/api/product-models/page?page=1&page_size=2",
        headers=headers,
    )
    assert first_page.status_code == 200, first_page.text
    assert first_page.json()["total"] == 3
    assert first_page.json()["total_pages"] == 2
    assert len(first_page.json()["items"]) == 2
    assert first_page.json()["items"][0]["category_name"] == "Test Safes"
    assert first_page.json()["items"][0]["template_name"].startswith(
        "Test Passport",
    )

    name_search = client.get(
        "/api/product-models/page?search=heritage",
        headers=headers,
    )
    assert [item["model_code"] for item in name_search.json()["items"]] == [
        "HERITAGE-1920",
    ]

    code_search = client.get(
        "/api/product-models/page?search=modern",
        headers=headers,
    )
    assert [item["model_code"] for item in code_search.json()["items"]] == [
        "MODERN-40",
    ]

    filtered = client.get(
        f"/api/product-models/page?category_id={safes.id}&status=archived",
        headers=headers,
    )
    assert filtered.status_code == 200, filtered.text
    assert [item["model_code"] for item in filtered.json()["items"]] == [
        "MODERN-40",
    ]


def test_product_model_can_update_and_clear_editable_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    category = create_category(db_session)
    template = create_template(db_session, user, category)
    create_response = client.post(
        "/api/product-models",
        headers=headers,
        json=product_model_data(category, template),
    )
    model_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/product-models/{model_id}",
        headers=headers,
        json={
            "name": "EveryDaySafe 40 Updated",
            "description": None,
            "status": "archived",
        },
    )

    assert update_response.status_code == 200, update_response.text
    result = update_response.json()
    assert result["name"] == "EveryDaySafe 40 Updated"
    assert result["description"] is None
    assert result["status"] == "archived"

    forbidden_change = client.put(
        f"/api/product-models/{model_id}",
        headers=headers,
        json={"model_code": "CHANGED"},
    )
    assert forbidden_change.status_code == 422


def test_product_model_code_is_unique_inside_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    category = create_category(db_session)
    template = create_template(db_session, user, category)
    request_data = product_model_data(category, template)

    first_response = client.post(
        "/api/product-models",
        headers=headers,
        json=request_data,
    )
    duplicate_response = client.post(
        "/api/product-models",
        headers=headers,
        json=request_data,
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "A product model with this code already exists",
    }
