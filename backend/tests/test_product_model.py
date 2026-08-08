from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, PassportTemplate, ProductCategory, ProductModel
from app.schemas.product_model import (
    ProductModelCreate,
    ProductModelResponse,
    ProductModelUpdate,
)


def test_product_model_is_persisted_with_exact_template_version(
    db_session: Session,
) -> None:
    organization = Organization(name="Example Manufacturer")
    category = ProductCategory(code="TEST_PRODUCTS", name="Test Products")
    template = PassportTemplate(
        organization=organization,
        category=category,
        name="Test Passport",
        status="active",
    )
    product_model = ProductModel(
        organization=organization,
        category=category,
        template=template,
        model_code="MODEL-100",
        name="Example Product",
        description="A shared description for every item of this model.",
    )
    db_session.add(product_model)
    db_session.commit()

    saved_model = db_session.scalar(
        select(ProductModel).where(ProductModel.id == product_model.id),
    )

    assert saved_model is not None
    assert saved_model.organization_id == organization.id
    assert saved_model.category_id == category.id
    assert saved_model.template_id == template.id
    assert saved_model.description == (
        "A shared description for every item of this model."
    )
    assert saved_model.status == "active"


def test_product_model_schemas_trim_and_serialize_values() -> None:
    create_data = ProductModelCreate(
        category_id="00000000-0000-0000-0000-000000000001",
        template_id="00000000-0000-0000-0000-000000000002",
        model_code="  MODEL-100  ",
        name="  Example Product  ",
        description="  A compact example product.  ",
    )

    assert create_data.model_code == "MODEL-100"
    assert create_data.name == "Example Product"
    assert create_data.description == "A compact example product."

    clear_description = ProductModelUpdate(description=None)
    assert "description" in clear_description.model_fields_set
    assert clear_description.description is None

    # Response schemas can read SQLAlchemy model attributes directly.
    assert ProductModelResponse.model_config["from_attributes"] is True
