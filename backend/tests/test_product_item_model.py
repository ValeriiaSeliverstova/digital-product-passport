from sqlalchemy.dialects import postgresql, sqlite

from app.models import ProductItem


def test_passport_data_uses_jsonb_only_on_postgresql() -> None:
    """Keep lightweight JSON tests while using queryable JSONB in production."""

    column_type = ProductItem.__table__.c.passport_data.type

    assert column_type.compile(dialect=sqlite.dialect()) == "JSON"
    assert column_type.compile(dialect=postgresql.dialect()) == "JSONB"
