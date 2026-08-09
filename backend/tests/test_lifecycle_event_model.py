from sqlalchemy.dialects import postgresql, sqlite

from app.models import LifecycleEvent, ProductItem


def test_lifecycle_event_uses_jsonb_only_on_postgresql() -> None:
    """Keep SQLite tests while storing queryable lifecycle data in PostgreSQL."""

    column_type = LifecycleEvent.__table__.c.event_data.type

    assert column_type.compile(dialect=sqlite.dialect()) == "JSON"
    assert column_type.compile(dialect=postgresql.dialect()) == "JSONB"


def test_lifecycle_event_relationship_and_constraints_are_registered() -> None:
    constraint_names = {
        constraint.name for constraint in LifecycleEvent.__table__.constraints
    }

    assert "ck_lifecycle_event_type" in constraint_names
    assert "ck_lifecycle_event_access_level" in constraint_names
    assert LifecycleEvent.product_item.property.back_populates == "lifecycle_events"
    assert ProductItem.lifecycle_events.property.back_populates == "product_item"
