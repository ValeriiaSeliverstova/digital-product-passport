from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Organization,
    PassportTemplate,
    ProductCategory,
    ProductItem,
    ProductModel,
    TemplateField,
)


def create_passport(
    db: Session,
    *,
    item_status: str = "published",
) -> ProductItem:
    """Create a product passport with both public and private fields."""

    organization = Organization(name="Example Safe Manufacturer")
    category = ProductCategory(
        code=f"SAFES_{uuid4().hex}",
        name="Safes",
    )
    template = PassportTemplate(
        organization=organization,
        category=category,
        name="Safe Passport",
        version=2,
        status="active",
        fields=[
            TemplateField(
                code="product_name",
                label="Product name",
                data_type="text",
                is_required=True,
                display_order=1,
                access_level="public",
                validation_rules={},
            ),
            TemplateField(
                code="weight_kg",
                label="Weight",
                data_type="decimal",
                display_order=2,
                access_level="public",
                validation_rules={},
            ),
            TemplateField(
                code="internal_note",
                label="Internal note",
                data_type="text",
                display_order=3,
                access_level="manufacturer",
                validation_rules={},
            ),
            TemplateField(
                code="optional_public_value",
                label="Optional value",
                data_type="text",
                display_order=4,
                access_level="public",
                validation_rules={},
            ),
        ],
    )
    product_model = ProductModel(
        organization=organization,
        category=category,
        template=template,
        model_code="EDS-40",
        name="EveryDaySafe 40",
        description="Compact safe for homes and small offices.",
    )
    product_item = ProductItem(
        organization=organization,
        product_model=product_model,
        serial_number=f"EDS-{uuid4().hex}",
        manufacture_date=date(2026, 8, 7),
        status=item_status,
        passport_data={
            "product_name": "EveryDaySafe 40",
            "weight_kg": 55.5,
            "internal_note": "Never return this value publicly",
        },
    )
    db.add(product_item)
    db.commit()
    return product_item


def test_published_passport_is_public_without_authentication(
    client: TestClient,
    db_session: Session,
) -> None:
    product_item = create_passport(db_session)

    response = client.get(f"/api/passports/{product_item.public_id}")

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["public_id"] == str(product_item.public_id)
    assert result["manufacturer_name"] == "Example Safe Manufacturer"
    assert result["category_name"] == "Safes"
    assert result["model_code"] == "EDS-40"
    assert result["model_name"] == "EveryDaySafe 40"
    assert result["template_name"] == "Safe Passport"
    assert result["template_version"] == 2
    assert result["serial_number"] == product_item.serial_number
    assert result["manufacture_date"] == "2026-08-07"
    assert result["fields"] == [
        {
            "code": "product_name",
            "label": "Product name",
            "data_type": "text",
            "value": "EveryDaySafe 40",
        },
        {
            "code": "weight_kg",
            "label": "Weight",
            "data_type": "decimal",
            "value": 55.5,
        },
    ]


def test_private_and_missing_fields_are_not_returned(
    client: TestClient,
    db_session: Session,
) -> None:
    product_item = create_passport(db_session)

    response = client.get(f"/api/passports/{product_item.public_id}")
    response_text = response.text

    assert response.status_code == 200
    assert "internal_note" not in response_text
    assert "Never return this value publicly" not in response_text
    assert "optional_public_value" not in response_text


def test_non_published_and_unknown_passports_return_not_found(
    client: TestClient,
    db_session: Session,
) -> None:
    draft = create_passport(db_session, item_status="draft")
    retired = create_passport(db_session, item_status="retired")

    responses = [
        client.get(f"/api/passports/{draft.public_id}"),
        client.get(f"/api/passports/{retired.public_id}"),
        client.get(f"/api/passports/{uuid4()}"),
    ]

    for response in responses:
        assert response.status_code == 404
        assert response.json() == {"detail": "Published passport not found"}
