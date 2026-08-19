from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, PasswordResetToken, Role, User
from app.security import (
    create_access_token,
    hash_password,
    hash_password_reset_token,
    verify_password,
)


TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "correct-horse-battery-staple"
RESET_TOKEN = "secure-password-reset-token-with-enough-entropy"
FORGOT_PASSWORD_MESSAGE = (
    "If an account with this email exists, password reset instructions have "
    "been sent."
)


def create_test_user(db: Session, *, status: str = "active") -> User:
    """Create a user with a real Argon2 hash for authentication tests."""

    role = Role(name="system_admin")
    user = User(
        email=TEST_EMAIL,
        password_hash=hash_password(TEST_PASSWORD),
        status=status,
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def test_login_and_read_current_user(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_test_user(db_session)

    login_response = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    assert login_response.status_code == 200
    assert login_response.headers["cache-control"] == "no-store"
    assert login_response.headers["pragma"] == "no-cache"
    token = login_response.json()["access_token"]
    assert login_response.json()["token_type"] == "bearer"

    # JWT payloads are signed, not encrypted. Only non-sensitive identity and
    # standard validation claims should be present.
    unverified_payload = jwt.decode(
        token,
        options={"verify_signature": False},
    )
    assert unverified_payload["sub"] == str(user.id)
    assert "password_hash" not in unverified_payload
    assert "role" not in unverified_payload

    me_response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == TEST_EMAIL
    assert me_response.json()["role"]["name"] == "system_admin"
    assert me_response.json()["organization"] is None
    assert "password_hash" not in me_response.json()


def test_current_user_response_includes_organization_name(
    client: TestClient,
    db_session: Session,
) -> None:
    role = Role(name="manufacturer_user")
    organization = Organization(name="Example Safety Institute")
    user = User(
        email="manufacturer@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        status="active",
        role=role,
        organization=organization,
    )
    db_session.add(user)
    db_session.commit()

    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
    )

    assert response.status_code == 200
    assert response.json()["organization"] == {
        "id": str(organization.id),
        "name": "Example Safety Institute",
        "country": None,
        "address_line_1": None,
        "address_line_2": None,
        "city": None,
        "postal_code": None,
        "contact_email": None,
        "phone": None,
        "website": None,
        "azure_devops_area_path": None,
        "azure_devops_work_item_type": "Customer Support",
        "has_logo": False,
        "logo_updated_at": None,
    }


def test_login_rejects_wrong_password(
    client: TestClient,
    db_session: Session,
) -> None:
    create_test_user(db_session)

    response = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        data={"username": "unknown@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_login_rejects_inactive_user(
    client: TestClient,
    db_session: Session,
) -> None:
    create_test_user(db_session, status="inactive")

    response = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
    )

    assert response.status_code == 401


def test_current_user_requires_valid_token(client: TestClient) -> None:
    missing_response = client.get("/api/users/me")
    invalid_response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert missing_response.status_code == 401
    assert invalid_response.status_code == 401


def test_current_user_rejects_inactive_account(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_test_user(db_session, status="inactive")
    token = create_access_token(user.id)

    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_current_user_can_change_password(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_test_user(db_session)
    token = create_access_token(user.id)
    new_password = "new-correct-horse-battery-staple"

    response = client.put(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": TEST_PASSWORD,
            "new_password": new_password,
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    db_session.refresh(user)
    assert verify_password(new_password, user.password_hash)

    old_login = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    new_login = client.post(
        "/api/auth/login",
        data={"username": TEST_EMAIL, "password": new_password},
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_password_change_rejects_wrong_current_password(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_test_user(db_session)
    original_password_hash = user.password_hash
    token = create_access_token(user.id)

    response = client.put(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "incorrect-current-password",
            "new_password": "new-correct-horse-battery-staple",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Current password is incorrect"}
    db_session.refresh(user)
    assert user.password_hash == original_password_hash


def test_password_change_rejects_reused_or_invalid_password(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_test_user(db_session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    reused_response = client.put(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": TEST_PASSWORD,
            "new_password": TEST_PASSWORD,
        },
    )
    short_response = client.put(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "too-short",
        },
    )

    assert reused_response.status_code == 400
    assert reused_response.json() == {
        "detail": "New password must be different from the current password",
    }
    assert short_response.status_code == 422


def test_password_change_requires_authentication(client: TestClient) -> None:
    response = client.put(
        "/api/users/me/password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "new-correct-horse-battery-staple",
        },
    )

    assert response.status_code == 401


def test_forgot_password_stores_only_hash_and_sends_email(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    user = create_test_user(db_session)
    sent: dict[str, str] = {}
    monkeypatch.setattr(
        "app.routers.auth.create_password_reset_token",
        lambda: RESET_TOKEN,
    )
    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email",
        lambda **values: sent.update(values),
    )

    response = client.post(
        "/api/auth/forgot-password",
        json={"email": f"  {TEST_EMAIL.upper()}  "},
    )

    assert response.status_code == 200
    assert response.json() == {"message": FORGOT_PASSWORD_MESSAGE}
    stored = db_session.scalar(select(PasswordResetToken))
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.token_hash == hash_password_reset_token(RESET_TOKEN)
    assert stored.token_hash != RESET_TOKEN
    assert stored.used_at is None
    assert sent == {"recipient": TEST_EMAIL, "reset_token": RESET_TOKEN}


def test_forgot_password_does_not_reveal_unknown_or_inactive_accounts(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    create_test_user(db_session, status="inactive")

    def fail_if_email_is_sent(**_values: str) -> None:
        raise AssertionError("An email must not be sent for an inactive account")

    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email",
        fail_if_email_is_sent,
    )

    unknown = client.post(
        "/api/auth/forgot-password",
        json={"email": "unknown@example.com"},
    )
    inactive = client.post(
        "/api/auth/forgot-password",
        json={"email": TEST_EMAIL},
    )

    expected = {"message": FORGOT_PASSWORD_MESSAGE}
    assert unknown.status_code == 200
    assert inactive.status_code == 200
    assert unknown.json() == expected
    assert inactive.json() == expected
    assert db_session.scalar(select(PasswordResetToken)) is None


def test_new_reset_request_invalidates_previous_unused_token(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    user = create_test_user(db_session)
    previous = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token("previous-token"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(previous)
    db_session.commit()
    monkeypatch.setattr(
        "app.routers.auth.create_password_reset_token",
        lambda: RESET_TOKEN,
    )
    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email",
        lambda **_values: None,
    )

    response = client.post(
        "/api/auth/forgot-password",
        json={"email": TEST_EMAIL},
    )

    assert response.status_code == 200
    db_session.refresh(previous)
    assert previous.used_at is not None
    stored_tokens = db_session.scalars(select(PasswordResetToken)).all()
    assert len(stored_tokens) == 2
    assert sum(token.used_at is None for token in stored_tokens) == 1


def test_reset_password_updates_password_and_consumes_token(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_test_user(db_session)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token(RESET_TOKEN),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(reset_token)
    db_session.commit()
    new_password = "a-new-secure-password"

    response = client.post(
        "/api/auth/reset-password",
        json={"token": RESET_TOKEN, "new_password": new_password},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Your password has been reset successfully.",
    }
    db_session.refresh(user)
    db_session.refresh(reset_token)
    assert verify_password(new_password, user.password_hash)
    assert reset_token.used_at is not None

    reused = client.post(
        "/api/auth/reset-password",
        json={"token": RESET_TOKEN, "new_password": "another-secure-password"},
    )
    assert reused.status_code == 400
    assert reused.json() == {
        "detail": "Password reset link is invalid or has expired.",
    }


def test_reset_password_rejects_invalid_expired_and_short_values(
    client: TestClient,
    db_session: Session,
) -> None:
    user = create_test_user(db_session)
    expired_token = "expired-password-reset-token-with-enough-entropy"
    db_session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_password_reset_token(expired_token),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        ),
    )
    db_session.commit()

    invalid = client.post(
        "/api/auth/reset-password",
        json={"token": RESET_TOKEN, "new_password": "a-new-secure-password"},
    )
    expired = client.post(
        "/api/auth/reset-password",
        json={"token": expired_token, "new_password": "a-new-secure-password"},
    )
    short = client.post(
        "/api/auth/reset-password",
        json={"token": RESET_TOKEN, "new_password": "too-short"},
    )

    expected = {"detail": "Password reset link is invalid or has expired."}
    assert invalid.status_code == 400
    assert expired.status_code == 400
    assert invalid.json() == expected
    assert expired.json() == expected
    assert short.status_code == 422
