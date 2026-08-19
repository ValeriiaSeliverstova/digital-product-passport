import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy.orm import Session

from app.models import ProductItem, SupportTicket
from tests.test_public_passport_api import create_passport


TRACKING_CODE = "private-code-123456"


def create_support_ticket(db: Session) -> SupportTicket:
    product_item = create_passport(db)
    support_ticket = SupportTicket(
        organization_id=product_item.organization_id,
        product_item_id=product_item.id,
        azure_ticket_id=991,
        idempotency_key="tracking-test-key",
        request_fingerprint="f" * 64,
        subject="Door does not close",
        tracking_code_hash=hashlib.sha256(TRACKING_CODE.encode()).hexdigest(),
        tracking_email_sent=True,
        created_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
    )
    db.add(support_ticket)
    db.commit()
    return support_ticket


def test_customer_can_track_ticket_with_correct_code(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    support_ticket = create_support_ticket(db_session)
    product_item = db_session.get(ProductItem, support_ticket.product_item_id)
    assert product_item is not None
    monkeypatch.setattr(
        "app.routers.support_tickets.get_support_work_item",
        lambda _ticket_id: {
            "System.State": "Active",
            "System.CreatedDate": "2026-08-13T12:00:00Z",
            "System.ChangedDate": "2026-08-13T14:30:00Z",
        },
    )
    monkeypatch.setattr(
        "app.routers.support_tickets.get_support_work_item_comments",
        lambda _ticket_id: [
            {
                "id": 10,
                "text": "@customer Engineer response",
                "createdDate": "2026-08-13T14:00:00Z",
            },
            {
                "id": 12,
                "text": "Internal engineer note",
                "createdDate": "2026-08-13T14:10:00Z",
            },
            {
                "id": 11,
                "text": "**Customer reply via DPP:**\n\nThank you",
                "createdDate": "2026-08-13T14:15:00Z",
            },
        ],
    )

    response = client.post(
        "/api/support-tickets/991/track",
        json={"tracking_code": TRACKING_CODE},
    )

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "ticket_id": 991,
        "subject": "Door does not close",
        "status": "Active",
        "is_closed": False,
        "submitted_at": "2026-08-13T12:00:00Z",
        "updated_at": "2026-08-13T14:30:00Z",
        "closed_at": None,
        "product_public_id": str(product_item.public_id),
        "comments": [
            {
                "id": 10,
                "author": "Support",
                "message": "Engineer response",
                "created_at": "2026-08-13T14:00:00Z",
            },
            {
                "id": 11,
                "author": "Customer",
                "message": "Thank you",
                "created_at": "2026-08-13T14:15:00Z",
            },
        ],
    }


def test_tracking_rejects_wrong_code_without_revealing_ticket_existence(
    client: TestClient,
    db_session: Session,
) -> None:
    create_support_ticket(db_session)

    wrong_code = client.post(
        "/api/support-tickets/991/track",
        json={"tracking_code": "wrong-code-1234567"},
    )
    unknown_ticket = client.post(
        "/api/support-tickets/992/track",
        json={"tracking_code": TRACKING_CODE},
    )

    assert wrong_code.status_code == 404
    assert unknown_ticket.status_code == 404
    assert wrong_code.json() == unknown_ticket.json()
    assert wrong_code.json() == {
        "detail": "Ticket number or tracking code is invalid",
    }


def test_tracking_rejects_ticket_from_another_product_context(
    client: TestClient,
    db_session: Session,
) -> None:
    create_support_ticket(db_session)

    response = client.post(
        "/api/support-tickets/991/track",
        json={
            "tracking_code": TRACKING_CODE,
            "product_public_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Ticket number or tracking code is invalid",
    }


def test_closed_ticket_tracking_returns_closure_date(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    support_ticket = create_support_ticket(db_session)
    product_item = db_session.get(ProductItem, support_ticket.product_item_id)
    assert product_item is not None
    monkeypatch.setattr(
        "app.routers.support_tickets.get_support_work_item",
        lambda _ticket_id: {
            "System.State": "Closed",
            "System.CreatedDate": "2026-08-13T12:00:00Z",
            "System.ChangedDate": "2026-08-15T09:30:00Z",
        },
    )
    monkeypatch.setattr(
        "app.routers.support_tickets.get_support_work_item_comments",
        lambda _ticket_id: [],
    )

    response = client.post(
        "/api/support-tickets/991/track",
        json={"tracking_code": TRACKING_CODE},
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "Closed"
    assert result["is_closed"] is True
    assert result["closed_at"] == "2026-08-15T09:30:00Z"
    assert result["product_public_id"] == str(product_item.public_id)


def test_customer_can_reply_with_correct_code(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    create_support_ticket(db_session)
    captured: dict[str, object] = {}

    def fake_add_comment(*, ticket_id: int, message: str) -> None:
        captured.update(ticket_id=ticket_id, message=message)

    monkeypatch.setattr(
        "app.routers.support_tickets.get_support_work_item",
        lambda _ticket_id: {
            "System.State": "Active",
            "System.CreatedDate": "2026-08-13T12:00:00Z",
        },
    )
    monkeypatch.setattr(
        "app.routers.support_tickets.add_support_work_item_comment",
        fake_add_comment,
    )

    response = client.post(
        "/api/support-tickets/991/comments",
        json={
            "tracking_code": TRACKING_CODE,
            "message": "The suggested fix worked.",
        },
    )

    assert response.status_code == 204, response.text
    assert captured == {
        "ticket_id": 991,
        "message": "The suggested fix worked.",
    }


def test_closed_ticket_rejects_customer_reply(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    create_support_ticket(db_session)
    comment_was_added = False

    monkeypatch.setattr(
        "app.routers.support_tickets.get_support_work_item",
        lambda _ticket_id: {
            "System.State": "Closed",
            "System.CreatedDate": "2026-08-13T12:00:00Z",
        },
    )

    def fake_add_comment(**_values: object) -> None:
        nonlocal comment_was_added
        comment_was_added = True

    monkeypatch.setattr(
        "app.routers.support_tickets.add_support_work_item_comment",
        fake_add_comment,
    )

    response = client.post(
        "/api/support-tickets/991/comments",
        json={
            "tracking_code": TRACKING_CODE,
            "message": "Can this ticket be reopened?",
        },
    )

    assert response.status_code == 409, response.text
    assert response.json() == {
        "detail": "Closed support tickets cannot receive new messages",
    }
    assert comment_was_added is False


def test_reply_rejects_wrong_code_and_invalid_message(
    client: TestClient,
    db_session: Session,
) -> None:
    create_support_ticket(db_session)

    wrong_code = client.post(
        "/api/support-tickets/991/comments",
        json={"tracking_code": "wrong-code-1234567", "message": "A reply"},
    )
    empty_message = client.post(
        "/api/support-tickets/991/comments",
        json={"tracking_code": TRACKING_CODE, "message": "   "},
    )

    assert wrong_code.status_code == 404
    assert empty_message.status_code == 422
