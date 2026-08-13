from fastapi.testclient import TestClient

from app.config import settings


def test_configured_frontend_origin_is_allowed(client: TestClient) -> None:
    """Allow the frontend preflight request to use bearer authentication."""

    response = client.options(
        "/api/templates",
        headers={
            "Origin": settings.frontend_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        settings.frontend_origin
    )


def test_unknown_frontend_origin_is_not_allowed(client: TestClient) -> None:
    """Do not grant browser access to origins outside our configuration."""

    response = client.options(
        "/api/templates",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_support_ticket_idempotency_header_is_allowed(client: TestClient) -> None:
    response = client.options(
        "/api/passports/00000000-0000-0000-0000-000000000000/support-tickets",
        headers={
            "Origin": settings.frontend_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Idempotency-Key",
        },
    )

    assert response.status_code == 200
    assert "Idempotency-Key" in response.headers["access-control-allow-headers"]
