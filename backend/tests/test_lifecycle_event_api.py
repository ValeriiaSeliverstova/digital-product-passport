from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LifecycleEvent
from tests.test_product_item_api import (
    create_item_through_api,
    create_manufacturer,
    create_product_model,
)


def publish_item(
    client: TestClient,
    headers: dict[str, str],
    item_id: str,
) -> None:
    response = client.put(
        f"/api/product-items/{item_id}",
        headers=headers,
        json={"status": "published"},
    )
    assert response.status_code == 200, response.text


def event_data(
    *,
    event_type: str = "maintenance",
    occurred_at: str = "2026-08-08T10:30:00+03:00",
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "occurred_at": occurred_at,
        "description": "Annual lock inspection completed",
        "service_provider": "Example Service Ltd.",
        "access_level": "public",
        "event_data": {"result": "passed"},
    }


def test_manufacturer_can_create_event_for_owned_published_item(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    item = create_item_through_api(client, headers, product_model)
    publish_item(client, headers, str(item["id"]))

    response = client.post(
        f"/api/product-items/{item['id']}/lifecycle-events",
        headers=headers,
        json=event_data(),
    )

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["item_id"] == item["id"]
    assert result["created_by_user_id"] == str(user.id)
    assert result["event_type"] == "maintenance"
    assert result["event_data"] == {"result": "passed"}

    stored_event = db_session.scalar(select(LifecycleEvent))
    assert stored_event is not None
    assert stored_event.created_by_user_id == user.id


def test_events_are_listed_newest_first(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    item = create_item_through_api(client, headers, product_model)
    item_id = str(item["id"])
    publish_item(client, headers, item_id)

    for event_type, occurred_at in (
        ("manufacturing", "2026-07-01T09:00:00Z"),
        ("inspection", "2026-08-01T09:00:00Z"),
    ):
        response = client.post(
            f"/api/product-items/{item_id}/lifecycle-events",
            headers=headers,
            json=event_data(
                event_type=event_type,
                occurred_at=occurred_at,
            ),
        )
        assert response.status_code == 201, response.text

    response = client.get(
        f"/api/product-items/{item_id}/lifecycle-events",
        headers=headers,
    )

    assert response.status_code == 200
    assert [event["event_type"] for event in response.json()] == [
        "inspection",
        "manufacturing",
    ]


def test_draft_item_rejects_lifecycle_events(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    item = create_item_through_api(client, headers, product_model)

    response = client.post(
        f"/api/product-items/{item['id']}/lifecycle-events",
        headers=headers,
        json=event_data(),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Lifecycle events require a published product item",
    }


def test_lifecycle_routes_hide_other_organizations(
    client: TestClient,
    db_session: Session,
) -> None:
    _, headers = create_manufacturer(db_session, "Manufacturer A")
    other_user, other_headers = create_manufacturer(
        db_session,
        "Manufacturer B",
    )
    other_model = create_product_model(db_session, other_user)
    item = create_item_through_api(client, other_headers, other_model)
    publish_item(client, other_headers, str(item["id"]))

    create_response = client.post(
        f"/api/product-items/{item['id']}/lifecycle-events",
        headers=headers,
        json=event_data(),
    )
    list_response = client.get(
        f"/api/product-items/{item['id']}/lifecycle-events",
        headers=headers,
    )

    assert create_response.status_code == 404
    assert list_response.status_code == 404


def test_lifecycle_event_input_is_validated(
    client: TestClient,
    db_session: Session,
) -> None:
    user, headers = create_manufacturer(db_session, "Manufacturer A")
    product_model = create_product_model(db_session, user)
    item = create_item_through_api(client, headers, product_model)
    item_id = str(item["id"])
    publish_item(client, headers, item_id)

    invalid_type = client.post(
        f"/api/product-items/{item_id}/lifecycle-events",
        headers=headers,
        json=event_data(event_type="unknown"),
    )
    missing_timezone = client.post(
        f"/api/product-items/{item_id}/lifecycle-events",
        headers=headers,
        json=event_data(occurred_at="2026-08-08T10:30:00"),
    )

    assert invalid_type.status_code == 422
    assert missing_timezone.status_code == 422


def test_lifecycle_routes_require_authentication(client: TestClient) -> None:
    item_id = "00000000-0000-0000-0000-000000000000"

    create_response = client.post(
        f"/api/product-items/{item_id}/lifecycle-events",
        json=event_data(),
    )
    list_response = client.get(
        f"/api/product-items/{item_id}/lifecycle-events",
    )

    assert create_response.status_code == 401
    assert list_response.status_code == 401
