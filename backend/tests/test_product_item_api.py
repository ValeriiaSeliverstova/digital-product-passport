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
    TemplateField,
    User,
)
from app.security import create_access_token
from app.config import settings


def create_manufacturer(
    db: Session,
    organization_name: str,
) -> tuple[User, dict[str, str]]:
    role = db.scalar(select(Role).where(Role.name == "manufacturer_user"))
    if role is None:
        role = Role(name="manufacturer_user")

    user = User(
        email=f"{uuid4()}@example.com",
        password_hash="not-used-by-product-item-api-tests",
        status="active",
        role=role,
        organization=Organization(name=organization_name),
    )
    db.add(user)
    db.commit()
    return user, {
        "Authorization": f"Bearer {create_access_token(user.id)}",
    }


def create_product_model(
    db: Session,
    user: User,
    *,
    model_status: str = "active",
    template_status: str = "active",
) -> ProductModel:
    category = ProductCategory(
        code=f"CATEGORY_{uuid4().hex}",
        name="Test Safes",
    )
    template = PassportTemplate(
        organization_id=user.organization_id,
        category=category,
        name=f"Safe Passport {uuid4()}",
        status=template_status,
        fields=[
            TemplateField(
                code="product_name",
                label="Product name",
                data_type="text",
                is_required=True,
                validation_rules={"min_length": 3, "max_length": 100},
            ),
            TemplateField(
                code="weight_kg",
                label="Weight",
                data_type="decimal",
                validation_rules={"min": 0, "max": 2000},
            ),
            TemplateField(
                code="certified",
                label="Certified",
                data_type="boolean",
                validation_rules={},
            ),
        ],
    )
    product_model = ProductModel(
        organization_id=user.organization_id,
        category=category,
        template=template,
        model_code=f"MODEL-{uuid4().hex}",
        name="EveryDaySafe 40",
        status=model_status,
    )
    db.add(product_model)
    db.commit()
    return product_model


def item_data(
    product_model: ProductModel,
    *,
    serial_number: str = "EDS-2026-0001",
) -> dict[str, object]:
    return {
        "model_id": str(product_model.id),
        "serial_number": serial_number,
        "manufacture_date": "2026-08-07",
        "passport_data": {
            "product_name": "EveryDaySafe 40",
            "weight_kg": 55.5,
            "certified": True,
        },
    }


def create_item_through_api(
    client: TestClient,
    headers: dict[str, str],
    product_model: ProductModel,
    *,
    serial_number: str = "EDS-2026-0001",
) -> dict[str, object]:
    response = client.post(
        "/api/product-items",
        headers=headers,
        json=item_data(product_model, serial_number=serial_number),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_product_item_creation_requires_authentication(
    client: TestClient,
    db_session: Session,
) -> None:
    user, _ = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)

    response = client.post(
        "/api/product-items",
        json=item_data(product_model),
    )

    assert response.status_code == 401


def test_product_item_is_created_as_owned_draft(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)

    result = create_item_through_api(client, headers, product_model)

    assert result["organization_id"] == str(user.organization_id)
    assert result["model_id"] == str(product_model.id)
    assert result["status"] == "draft"
    assert result["public_id"]
    assert result["passport_data"]["weight_kg"] == 55.5


def test_product_item_rejects_invalid_passport_data(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)

    test_cases = [
        (
            {"unknown_field": "value"},
            "Unknown passport field: unknown_field",
        ),
        (
            {"product_name": 123},
            "Passport field 'product_name' must be text",
        ),
        (
            {"weight_kg": -1},
            "Passport field 'weight_kg' must be at least 0",
        ),
    ]

    for index, (passport_data, expected_detail) in enumerate(test_cases):
        request_data = item_data(
            product_model,
            serial_number=f"INVALID-{index}",
        )
        request_data["passport_data"] = passport_data
        response = client.post(
            "/api/product-items",
            headers=headers,
            json=request_data,
        )

        assert response.status_code == 422
        assert response.json() == {"detail": expected_detail}


def test_product_item_requires_owned_active_model_and_template(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, _ = create_manufacturer(db_session, "Manufacturer B")
    other_model = create_product_model(db_session, other_user)
    archived_model = create_product_model(
        db_session,
        user,
        model_status="archived",
    )
    archived_template_model = create_product_model(
        db_session,
        user,
        template_status="archived",
    )

    other_response = client.post(
        "/api/product-items",
        headers=headers,
        json=item_data(other_model),
    )
    archived_model_response = client.post(
        "/api/product-items",
        headers=headers,
        json=item_data(archived_model),
    )
    archived_template_response = client.post(
        "/api/product-items",
        headers=headers,
        json=item_data(archived_template_model),
    )

    assert other_response.status_code == 404
    assert archived_model_response.status_code == 409
    assert archived_template_response.status_code == 409


def test_product_item_queries_hide_other_organizations(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, other_headers = create_manufacturer(
        db_session,
        "Manufacturer B",
    )
    product_model = create_product_model(db_session, user)
    other_model = create_product_model(db_session, other_user)
    owned = create_item_through_api(client, headers, product_model)
    other = create_item_through_api(
        client,
        other_headers,
        other_model,
        serial_number="OTHER-0001",
    )

    list_response = client.get("/api/product-items", headers=headers)
    other_response = client.get(
        f"/api/product-items/{other['id']}",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [
        owned["id"],
    ]
    assert other_response.status_code == 404


def test_product_item_list_supports_filters_and_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    first = create_item_through_api(
        client,
        headers,
        product_model,
        serial_number="SAFE-ALPHA",
    )
    second = create_item_through_api(
        client,
        headers,
        product_model,
        serial_number="SAFE-BETA",
    )
    publish = client.put(
        f"/api/product-items/{second['id']}",
        headers=headers,
        json={"status": "published"},
    )
    assert publish.status_code == 200

    filtered = client.get(
        "/api/product-items",
        headers=headers,
        params={
            "search": "beta",
            "status": "published",
            "manufactured_from": "2026-08-01",
            "manufactured_to": "2026-08-31",
            "page": 1,
            "page_size": 1,
        },
    )

    assert filtered.status_code == 200, filtered.text
    result = filtered.json()
    assert result["total"] == 1
    assert result["total_pages"] == 1
    assert result["items"][0]["id"] == second["id"]
    assert result["items"][0]["model_name"] == "EveryDaySafe 40"
    assert "passport_data" not in result["items"][0]

    first_page = client.get(
        "/api/product-items?page=1&page_size=1",
        headers=headers,
    )
    second_page = client.get(
        "/api/product-items?page=2&page_size=1",
        headers=headers,
    )
    assert first_page.json()["total"] == 2
    assert first_page.json()["total_pages"] == 2
    assert len(first_page.json()["items"]) == 1
    assert len(second_page.json()["items"]) == 1

    invalid_range = client.get(
        "/api/product-items?manufactured_from=2026-09-01&manufactured_to=2026-08-01",
        headers=headers,
    )
    assert invalid_range.status_code == 422


def test_required_fields_are_enforced_when_item_is_published(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    request_data = item_data(product_model)
    request_data["passport_data"] = {"weight_kg": 55.5}
    create_response = client.post(
        "/api/product-items",
        headers=headers,
        json=request_data,
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["id"]

    incomplete_publish = client.put(
        f"/api/product-items/{item_id}",
        headers=headers,
        json={"status": "published"},
    )
    complete_publish = client.put(
        f"/api/product-items/{item_id}",
        headers=headers,
        json={
            "passport_data": {
                "product_name": "EveryDaySafe 40",
                "weight_kg": 55.5,
            },
            "status": "published",
        },
    )

    assert incomplete_publish.status_code == 422
    assert incomplete_publish.json() == {
        "detail": "Required passport field is missing: product_name",
    }
    assert complete_publish.status_code == 200
    assert complete_publish.json()["status"] == "published"


def test_published_item_can_only_be_retired(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    item = create_item_through_api(client, headers, product_model)
    item_id = item["id"]
    publish_response = client.put(
        f"/api/product-items/{item_id}",
        headers=headers,
        json={"status": "published"},
    )
    assert publish_response.status_code == 200

    edit_response = client.put(
        f"/api/product-items/{item_id}",
        headers=headers,
        json={"serial_number": "CHANGED"},
    )
    retire_response = client.put(
        f"/api/product-items/{item_id}",
        headers=headers,
        json={"status": "retired"},
    )
    retired_edit = client.put(
        f"/api/product-items/{item_id}",
        headers=headers,
        json={"status": "published"},
    )

    assert edit_response.status_code == 409
    assert retire_response.status_code == 200
    assert retire_response.json()["status"] == "retired"
    assert retired_edit.status_code == 409


def test_serial_number_is_unique_inside_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    create_item_through_api(client, headers, product_model)

    duplicate = client.post(
        "/api/product-items",
        headers=headers,
        json=item_data(product_model),
    )

    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "A product item with this serial number already exists",
    }


def test_qr_code_is_generated_for_an_owned_published_item(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    item = create_item_through_api(client, headers, product_model)
    item_id = item["id"]

    draft_response = client.get(
        f"/api/product-items/{item_id}/qr-code",
        headers=headers,
    )
    assert draft_response.status_code == 409

    publish_response = client.put(
        f"/api/product-items/{item_id}",
        headers=headers,
        json={"status": "published"},
    )
    assert publish_response.status_code == 200

    encoded_urls = []

    def fake_qr_code(public_url: str) -> bytes:
        encoded_urls.append(public_url)
        return b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'

    monkeypatch.setattr(
        "app.routers.product_items.create_qr_code_svg",
        fake_qr_code,
    )
    response = client.get(
        f"/api/product-items/{item_id}/qr-code",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].endswith('.svg"')
    assert encoded_urls == [
        f"{settings.frontend_origin}/passport/{item['public_id']}",
    ]


def test_qr_code_endpoint_hides_other_organizations(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, other_headers = create_manufacturer(
        db_session,
        "Manufacturer B",
    )
    other_model = create_product_model(db_session, other_user)
    other_item = create_item_through_api(
        client,
        other_headers,
        other_model,
    )

    response = client.get(
        f"/api/product-items/{other_item['id']}/qr-code",
        headers=headers,
    )

    assert response.status_code == 404
