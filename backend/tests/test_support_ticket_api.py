from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from app.azure_devops import (
    AzureDevOpsNotConfiguredError,
    AzureDevOpsRequestError,
)
from app.email_delivery import EmailDeliveryError
from tests.test_public_passport_api import create_passport
from app.models import SupportTicket
from app.support_ticket_protection import support_ticket_guard


TICKET_DATA = {
    "requester_name": "Taylor Customer",
    "requester_email": "TAYLOR@EXAMPLE.COM",
    "subject": "Door does not close",
    "message": "The safe door no longer closes correctly.",
}


@pytest.fixture(autouse=True)
def reset_support_ticket_guard(monkeypatch: MonkeyPatch) -> None:
    """Isolate process-local state and SMTP delivery in API tests."""

    support_ticket_guard.clear()
    monkeypatch.setattr(
        "app.routers.passports.tracking_email_is_configured",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.routers.passports.send_tracking_email",
        lambda **_values: None,
    )


def idempotency_headers(key: str | None = None) -> dict[str, str]:
    return {"Idempotency-Key": key or str(uuid4())}


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
        headers=idempotency_headers(),
    )

    assert response.status_code == 201, response.text
    assert response.json() == {"ticket_id": 421}
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
    stored_ticket = db_session.query(SupportTicket).one()
    assert stored_ticket.azure_ticket_id == 421
    assert stored_ticket.product_item_id == product_item.id
    assert stored_ticket.tracking_email_sent is True
    assert len(stored_ticket.tracking_code_hash) == 64


def test_support_ticket_requires_a_published_passport(
    client: TestClient,
    db_session: Session,
) -> None:
    draft = create_passport(db_session, item_status="draft")

    draft_response = client.post(
        f"/api/passports/{draft.public_id}/support-tickets",
        json=TICKET_DATA,
        headers=idempotency_headers(),
    )
    unknown_response = client.post(
        f"/api/passports/{uuid4()}/support-tickets",
        json=TICKET_DATA,
        headers=idempotency_headers(),
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
        headers=idempotency_headers(),
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
        headers=idempotency_headers(),
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
        headers=idempotency_headers(),
    )

    assert response.status_code == 422


def test_repeated_idempotency_key_returns_ticket_without_duplicate_creation(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    product_item = create_passport(db_session)
    product_item.organization.azure_devops_area_path = "Students\\Support"
    db_session.commit()
    creation_count = 0

    def fake_create_support_work_item(**_values: object) -> tuple[int, None]:
        nonlocal creation_count
        creation_count += 1
        return 501, None

    monkeypatch.setattr(
        "app.routers.passports.create_support_work_item",
        fake_create_support_work_item,
    )
    headers = idempotency_headers("same-ticket-request")

    first = client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json=TICKET_DATA,
        headers=headers,
    )
    repeated = client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json=TICKET_DATA,
        headers=headers,
    )

    assert first.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json() == {"ticket_id": 501}
    assert creation_count == 1


def test_idempotency_key_cannot_be_reused_for_changed_ticket_data(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    product_item = create_passport(db_session)
    product_item.organization.azure_devops_area_path = "Students\\Support"
    db_session.commit()
    monkeypatch.setattr(
        "app.routers.passports.create_support_work_item",
        lambda **_values: (502, None),
    )
    headers = idempotency_headers("reused-ticket-key")
    client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json=TICKET_DATA,
        headers=headers,
    )

    response = client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json={**TICKET_DATA, "subject": "A different problem"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Idempotency key was already used for different ticket data",
    }


def test_support_ticket_rate_limit_rejects_sixth_attempt(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    product_item = create_passport(db_session)
    product_item.organization.azure_devops_area_path = "Students\\Support"
    db_session.commit()
    next_ticket_id = iter(range(503, 508))
    monkeypatch.setattr(
        "app.routers.passports.create_support_work_item",
        lambda **_values: (next(next_ticket_id), None),
    )
    url = f"/api/passports/{product_item.public_id}/support-tickets"

    allowed = [
        client.post(url, json=TICKET_DATA, headers=idempotency_headers())
        for _ in range(5)
    ]
    limited = client.post(url, json=TICKET_DATA, headers=idempotency_headers())

    assert all(response.status_code == 201 for response in allowed)
    assert limited.status_code == 429
    assert limited.json() == {
        "detail": "Too many support ticket requests. Please try again later.",
    }
    assert 1 <= int(limited.headers["retry-after"]) <= 600


def test_support_ticket_requires_idempotency_key(
    client: TestClient,
    db_session: Session,
) -> None:
    product_item = create_passport(db_session)

    response = client.post(
        f"/api/passports/{product_item.public_id}/support-tickets",
        json=TICKET_DATA,
    )

    assert response.status_code == 422


def test_email_failure_retry_does_not_create_second_azure_ticket(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    product_item = create_passport(db_session)
    product_item.organization.azure_devops_area_path = "Students\\Support"
    db_session.commit()
    azure_creation_count = 0
    email_attempt_count = 0

    def fake_create_support_work_item(**_values: object) -> tuple[int, None]:
        nonlocal azure_creation_count
        azure_creation_count += 1
        return 601, None

    def sometimes_fail_email(**_values: object) -> None:
        nonlocal email_attempt_count
        email_attempt_count += 1
        if email_attempt_count == 1:
            raise EmailDeliveryError

    monkeypatch.setattr(
        "app.routers.passports.create_support_work_item",
        fake_create_support_work_item,
    )
    monkeypatch.setattr(
        "app.routers.passports.send_tracking_email",
        sometimes_fail_email,
    )
    headers = idempotency_headers("retry-email-ticket")
    url = f"/api/passports/{product_item.public_id}/support-tickets"

    failed_email = client.post(url, json=TICKET_DATA, headers=headers)
    retry = client.post(url, json=TICKET_DATA, headers=headers)

    assert failed_email.status_code == 502
    assert retry.status_code == 201
    assert retry.json() == {"ticket_id": 601}
    assert azure_creation_count == 1
    assert email_attempt_count == 2
    assert db_session.query(SupportTicket).one().tracking_email_sent is True
