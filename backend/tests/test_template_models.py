from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.models import (
    Organization,
    PassportTemplate,
    ProductCategory,
    TemplateField,
)


def test_template_and_fields_are_persisted(db_session: Session) -> None:
    organization = Organization(name="Example Manufacturer")
    category = ProductCategory(code="TEST_SAFES", name="Test Safes")
    template = PassportTemplate(
        organization=organization,
        category=category,
        name="Standard Safe Passport",
    )
    template.fields = [
        TemplateField(
            code="weight_kg",
            label="Weight",
            data_type="decimal",
            is_required=True,
            display_order=2,
            validation_rules={"min": 0},
        ),
        TemplateField(
            code="lock_type",
            label="Lock Type",
            data_type="text",
            display_order=1,
            validation_rules={
                "allowed_values": ["Mechanical", "Electronic"],
            },
        ),
    ]
    db_session.add(template)
    db_session.commit()

    db_session.expire_all()
    saved_template = db_session.scalar(
        select(PassportTemplate).where(PassportTemplate.id == template.id),
    )

    assert saved_template is not None
    assert saved_template.version == 1
    assert saved_template.status == "draft"
    assert [field.code for field in saved_template.fields] == [
        "lock_type",
        "weight_kg",
    ]
    assert saved_template.fields[1].validation_rules == {"min": 0}


def test_validation_rules_use_jsonb_only_on_postgresql() -> None:
    column_type = TemplateField.__table__.c.validation_rules.type

    assert column_type.compile(dialect=sqlite.dialect()) == "JSON"
    assert column_type.compile(dialect=postgresql.dialect()) == "JSONB"
