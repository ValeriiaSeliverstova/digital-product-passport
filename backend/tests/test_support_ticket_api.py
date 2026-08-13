from uuid import uuid4

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from app.azure_devops import (
    AzureDevOpsNotConfiguredError,
    AzureDevOpsRequestError,
)
from tests.test_public_passport_api import create_passport


TICKET_DATA = {
    "requester_name": "Taylor Customer",
    "requester_email": "TAYLOR@EXAMPLE.COM",
    "subject": "Door does not close",
    "message": "The safe door no longer closes correctly.",
}


def test_public_passport_can_submit_enriched_support_ticket(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    product_item = create_passport(db_session)
    product_item.organization.azure_devops_area_path = "Students\\Safety Institute"
    db_session.commit()
    captured: dict[str, object] = {}

    def fake_create_support_work_item(**values: object) -> tuple[int, str]:
        captured.update(values)
        return 421, "https://dev.azure.com/what-software/Students/_workitems/edit/421"

    monkeypatch.setattr(
        "app.routers.passports.create_support_work_item",
        fake_create_support_work_item,
    )

    response = client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json=TICKET_DATA,
    )

    assert response.status_code == 201, response.text
    assert response.json() == {
        "ticket_id": 421,
        "ticket_url": (
            "https://dev.azure.com/what-software/Students/_workitems/edit/421"
        ),
    }
    assert captured["area_path"] == "Students\\Safety Institute"
    assert captured["work_item_type"] == "Customer Support"
    assert captured["requester_email"] == "taylor@example.com"
    assert captured["manufacturer_name"] == "Example Safe Manufacturer"
    assert captured["category_name"] == "Safes"
    assert captured["model_code"] == "EDS-40"
    assert captured["model_name"] == "EveryDaySafe 40"
    assert captured["serial_number"] == product_item.serial_number
    assert captured["public_id"] == str(product_item.public_id)
    assert captured["passport_url"].endswith(f"/passport/{product_item.public_id}")


def test_support_ticket_requires_a_published_passport(
    client: TestClient,
    db_session: Session,
) -> None:
    draft = create_passport(db_session, item_status="draft")

    draft_response = client.post(
        f"/api/passports/{draft.public_id}/support-tickets",
        json=TICKET_DATA,
    )
    unknown_response = client.post(
        f"/api/passports/{uuid4()}/support-tickets",
        json=TICKET_DATA,
    )

    assert draft_response.status_code == 404
    assert unknown_response.status_code == 404


def test_support_ticket_reports_safe_configuration_and_upstream_errors(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    product_item = create_passport(db_session)

    def raise_not_configured(**_values: object) -> None:
        raise AzureDevOpsNotConfiguredError

    monkeypatch.setattr(
        "app.routers.passports.create_support_work_item",
        raise_not_configured,
    )
    not_configured = client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json=TICKET_DATA,
    )

    def raise_upstream_error(**_values: object) -> None:
        raise AzureDevOpsRequestError

    monkeypatch.setattr(
        "app.routers.passports.create_support_work_item",
        raise_upstream_error,
    )
    upstream_error = client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json=TICKET_DATA,
    )

    assert not_configured.status_code == 503
    assert not_configured.json() == {
        "detail": "Support ticket service is not configured",
    }
    assert upstream_error.status_code == 502
    assert upstream_error.json() == {
        "detail": "Support ticket could not be submitted",
    }


def test_support_ticket_validates_customer_input(
    client: TestClient,
    db_session: Session,
) -> None:
    product_item = create_passport(db_session)

    response = client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json={**TICKET_DATA, "requester_email": "not-an-email", "message": "short"},
    )

    assert response.status_code == 422
