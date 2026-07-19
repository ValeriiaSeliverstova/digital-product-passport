import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Role, User
from app.security import hash_password


TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "correct-horse-battery-staple"


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
    assert "password_hash" not in me_response.json()


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
