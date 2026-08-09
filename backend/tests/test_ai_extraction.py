from uuid import uuid4

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_extraction import (
    RawExtraction,
    RawFieldSuggestion,
    RawIdentitySuggestions,
    RawSuggestion,
    validate_extraction,
)
from app.models import (
    Organization,
    PassportTemplate,
    ProductCategory,
    ProductModel,
    Role,
    TemplateField,
    User,
)
from app.schemas.ai_extraction import (
    AiExtractionResponse,
    AiFieldSuggestion,
    AiIdentitySuggestions,
    AiSuggestedValue,
)
from app.security import create_access_token


def create_manufacturer(
    db: Session,
    organization_name: str,
) -> tuple[User, dict[str, str]]:
    role = db.scalar(select(Role).where(Role.name == "manufacturer_user"))
    if role is None:
        role = Role(name="manufacturer_user")
    user = User(
        email=f"{uuid4()}@example.com",
        password_hash="not-used-by-ai-extraction-tests",
        status="active",
        role=role,
        organization=Organization(name=organization_name),
    )
    db.add(user)
    db.commit()
    return user, {"Authorization": f"Bearer {create_access_token(user.id)}"}


def create_model_with_fields(db: Session, user: User) -> ProductModel:
    category = ProductCategory(
        code=f"AI_{uuid4().hex}",
        name="AI Test Safes",
    )
    template = PassportTemplate(
        organization_id=user.organization_id,
        category=category,
        name="AI Test Passport",
        status="active",
        fields=[
            TemplateField(
                code="product_name",
                label="Product name",
                data_type="text",
                is_required=True,
                display_order=1,
                validation_rules={"min_length": 2, "max_length": 100},
            ),
            TemplateField(
                code="weight_kg",
                label="Weight, kg",
                data_type="decimal",
                is_required=True,
                display_order=2,
                validation_rules={"min": 0, "max": 2000},
            ),
            TemplateField(
                code="fire_resistant",
                label="Fire resistant",
                data_type="boolean",
                display_order=3,
                validation_rules={},
            ),
        ],
    )
    product_model = ProductModel(
        organization_id=user.organization_id,
        category=category,
        template=template,
        model_code="AI-SAFE-1",
        name="AI Test Safe",
    )
    db.add(product_model)
    db.commit()
    return product_model


def test_ai_extraction_requires_authentication(
    client: TestClient,
    db_session: Session,
) -> None:
    user, _ = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_model_with_fields(db_session, user)

    response = client.post(
        f"/api/product-models/{product_model.id}/ai-extraction",
        files={"document": ("safe.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 401


def test_ai_extraction_returns_reviewable_suggestions(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_model_with_fields(db_session, user)
    expected = AiExtractionResponse(
        identity=AiIdentitySuggestions(
            serial_number=AiSuggestedValue(
                value="SN-100",
                confidence="high",
                source="Page 1",
            ),
        ),
        fields=[
            AiFieldSuggestion(
                field_code="weight_kg",
                field_label="Weight, kg",
                value=485.5,
                confidence="high",
                source="Page 2",
            ),
        ],
        missing_required_fields=["product_name"],
    )
    received: dict[str, object] = {}

    def fake_extract(data: bytes, mime_type: str, model: ProductModel):
        received.update(data=data, mime_type=mime_type, model_id=model.id)
        return expected

    monkeypatch.setattr("app.routers.ai_extraction.extract_document", fake_extract)

    response = client.post(
        f"/api/product-models/{product_model.id}/ai-extraction",
        headers=headers,
        files={"document": ("safe.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 200, response.text
    assert response.json() == expected.model_dump(mode="json")
    assert received == {
        "data": b"%PDF-test",
        "mime_type": "application/pdf",
        "model_id": product_model.id,
    }


def test_ai_extraction_hides_another_organization_model(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, _ = create_manufacturer(db_session, "Manufacturer B")
    product_model = create_model_with_fields(db_session, other_user)

    response = client.post(
        f"/api/product-models/{product_model.id}/ai-extraction",
        headers=headers,
        files={"document": ("safe.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 404


def test_ai_extraction_rejects_unsupported_file(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_model_with_fields(db_session, user)

    response = client.post(
        f"/api/product-models/{product_model.id}/ai-extraction",
        headers=headers,
        files={"document": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("Source document must be")


def test_ai_values_are_converted_and_invalid_values_are_omitted() -> None:
    fields = [
        TemplateField(
            code="weight_kg",
            label="Weight, kg",
            data_type="decimal",
            is_required=True,
            display_order=1,
            validation_rules={"min": 0, "max": 2000},
        ),
        TemplateField(
            code="fire_resistant",
            label="Fire resistant",
            data_type="boolean",
            is_required=True,
            display_order=2,
            validation_rules={},
        ),
    ]
    raw = RawExtraction(
        identity=RawIdentitySuggestions(
            manufacture_date=RawSuggestion(
                value="not-a-date",
                confidence="low",
            ),
        ),
        fields=[
            RawFieldSuggestion(
                field_code="weight_kg",
                value="485.5",
                confidence="high",
                source="Specifications table",
            ),
            RawFieldSuggestion(
                field_code="fire_resistant",
                value="perhaps",
                confidence="low",
            ),
            RawFieldSuggestion(
                field_code="invented_field",
                value="invented value",
                confidence="low",
            ),
        ],
    )

    result = validate_extraction(raw, fields)

    assert result.fields[0].field_code == "weight_kg"
    assert result.fields[0].value == 485.5
    assert result.missing_required_fields == ["fire_resistant"]
    assert "Ignored invalid manufacture date" in result.warnings
    assert "Ignored invalid value for field: fire_resistant" in result.warnings
    assert "Ignored unknown field: invented_field" in result.warnings
