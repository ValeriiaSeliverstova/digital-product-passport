from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmailConfirmationToken, Organization, Role, User
from app.security import hash_email_confirmation_token, verify_password


SIGNUP_URL = "/api/auth/signup"
CONFIRM_URL = "/api/auth/confirm-email"
SIGNUP_EMAIL = "anna@example.com"
SIGNUP_PASSWORD = "correct-horse-battery-staple"
CONFIRMATION_TOKEN = "secure-email-confirmation-token-with-entropy"
DUPLICATE_EMAIL_MESSAGE = "An account with this email already exists."


def signup_payload(**overrides: object) -> dict[str, object]:
    """Build a valid signup body that individual tests can adjust."""

    payload: dict[str, object] = {
        "first_name": "Anna",
        "last_name": "Smith",
        "email": SIGNUP_EMAIL,
        "password": SIGNUP_PASSWORD,
        "organization_name": "Example Ltd.",
    }
    payload.update(overrides)
    return payload


def seed_roles(db: Session) -> Role:
    """Create the roles a real deployment seeds before signup is reachable."""

    manufacturer_role = Role(name="manufacturer_user")
    db.add_all([manufacturer_role, Role(name="system_admin")])
    db.commit()
    return manufacturer_role


def test_signup_creates_pending_manufacturer_with_new_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    manufacturer_role = seed_roles(db_session)

    response = client.post(SIGNUP_URL, json=signup_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == SIGNUP_EMAIL
    assert body["first_name"] == "Anna"
    assert body["last_name"] == "Smith"
    # The account stays unusable until the emailed link is opened.
    assert body["status"] == "pending"
    assert body["role"] == "manufacturer_user"
    assert body["organization_name"] == "Example Ltd."

    user = db_session.scalar(select(User).where(User.email == SIGNUP_EMAIL))
    assert user is not None
    assert user.role_id == manufacturer_role.id
    assert user.status == "pending"

    organization = db_session.scalar(select(Organization))
    assert organization is not None
    assert organization.name == "Example Ltd."
    assert user.organization_id == organization.id


def test_signup_stores_only_a_password_hash(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_roles(db_session)

    response = client.post(SIGNUP_URL, json=signup_payload())

    assert response.status_code == 201, response.text
    # Neither the raw password nor its hash may appear in the response, and the
    # body must expose no field beyond the safe account summary.
    user = db_session.scalar(select(User).where(User.email == SIGNUP_EMAIL))
    assert user is not None
    assert SIGNUP_PASSWORD not in response.text
    assert user.password_hash not in response.text
    assert set(response.json()) == {
        "id",
        "email",
        "first_name",
        "last_name",
        "status",
        "role",
        "organization_id",
        "organization_name",
    }

    assert user.password_hash != SIGNUP_PASSWORD
    assert verify_password(SIGNUP_PASSWORD, user.password_hash)


def login_attempt(client: TestClient) -> object:
    """Try the existing login flow with the credentials used at signup."""

    return client.post(
        "/api/auth/login",
        data={
            "grant_type": "password",
            "username": SIGNUP_EMAIL,
            "password": SIGNUP_PASSWORD,
        },
    )


def test_signup_blocks_login_until_the_email_is_confirmed(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_roles(db_session)
    created = client.post(SIGNUP_URL, json=signup_payload())
    assert created.status_code == 201, created.text
    # Signup must not hand back a session; the user has to log in separately.
    assert "access_token" not in created.json()

    blocked = login_attempt(client)

    assert blocked.status_code == 401


def test_confirmed_account_can_use_the_existing_login_flow(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    seed_roles(db_session)
    monkeypatch.setattr(
        "app.routers.auth.create_email_confirmation_token",
        lambda: CONFIRMATION_TOKEN,
    )
    client.post(SIGNUP_URL, json=signup_payload())

    confirmed = client.post(
        CONFIRM_URL,
        json={"token": CONFIRMATION_TOKEN},
    )
    response = login_attempt(client)

    assert confirmed.status_code == 200
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_confirmation_stores_only_a_hash_and_is_single_use(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    seed_roles(db_session)
    monkeypatch.setattr(
        "app.routers.auth.create_email_confirmation_token",
        lambda: CONFIRMATION_TOKEN,
    )
    client.post(SIGNUP_URL, json=signup_payload())

    stored = db_session.scalar(select(EmailConfirmationToken))
    assert stored is not None
    assert stored.token_hash == hash_email_confirmation_token(CONFIRMATION_TOKEN)
    assert stored.token_hash != CONFIRMATION_TOKEN

    first = client.post(CONFIRM_URL, json={"token": CONFIRMATION_TOKEN})
    replayed = client.post(CONFIRM_URL, json={"token": CONFIRMATION_TOKEN})

    assert first.status_code == 200
    # A confirmation link must not work twice.
    assert replayed.status_code == 400


def test_confirmation_rejects_unknown_and_expired_tokens(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    seed_roles(db_session)
    monkeypatch.setattr(
        "app.routers.auth.create_email_confirmation_token",
        lambda: CONFIRMATION_TOKEN,
    )
    client.post(SIGNUP_URL, json=signup_payload())
    expired = db_session.scalar(select(EmailConfirmationToken))
    assert expired is not None
    expired.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    unknown = client.post(CONFIRM_URL, json={"token": "x" * 43})
    stale = client.post(CONFIRM_URL, json={"token": CONFIRMATION_TOKEN})

    assert unknown.status_code == 400
    assert stale.status_code == 400
    user = db_session.scalar(select(User).where(User.email == SIGNUP_EMAIL))
    assert user is not None
    assert user.status == "pending"


def test_signup_rejects_a_duplicate_email_regardless_of_case(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_roles(db_session)
    first = client.post(SIGNUP_URL, json=signup_payload())

    duplicate = client.post(
        SIGNUP_URL,
        json=signup_payload(email=f"  {SIGNUP_EMAIL.upper()}  "),
    )

    assert first.status_code == 201, first.text
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == DUPLICATE_EMAIL_MESSAGE
    # A rejected signup must never create a second organization, whether it is
    # stopped by the pre-check or by the unique email constraint.
    assert len(db_session.scalars(select(Organization)).all()) == 1


def test_signup_rejects_a_password_below_the_existing_minimum(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_roles(db_session)

    response = client.post(SIGNUP_URL, json=signup_payload(password="short"))

    assert response.status_code == 422
    assert db_session.scalar(select(User)) is None
    assert db_session.scalar(select(Organization)) is None


def test_signup_rejects_missing_and_blank_required_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_roles(db_session)
    incomplete = signup_payload()
    del incomplete["organization_name"]

    missing = client.post(SIGNUP_URL, json=incomplete)
    blank = client.post(SIGNUP_URL, json=signup_payload(first_name="   "))
    invalid_email = client.post(SIGNUP_URL, json=signup_payload(email="anna"))

    assert missing.status_code == 422
    assert blank.status_code == 422
    assert invalid_email.status_code == 422
    assert db_session.scalar(select(User)) is None


def test_signup_cannot_choose_a_role_organization_or_status(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_roles(db_session)
    admin_role = db_session.scalar(
        select(Role).where(Role.name == "system_admin"),
    )
    assert admin_role is not None

    escalations = [
        signup_payload(role="system_admin"),
        signup_payload(role_id=str(admin_role.id)),
        signup_payload(organization_id="11111111-1111-1111-1111-111111111111"),
        signup_payload(status="inactive"),
    ]

    for payload in escalations:
        response = client.post(SIGNUP_URL, json=payload)
        # Unknown keys are forbidden, so privileged fields never reach the
        # model. Pin the reason so a future schema change cannot pass this
        # test by rejecting the request for some unrelated cause.
        assert response.status_code == 422, payload
        assert response.json()["detail"][0]["type"] == "extra_forbidden"

    assert db_session.scalar(select(User)) is None
    assert db_session.scalar(select(Organization)) is None


def test_signup_always_assigns_the_manufacturer_role(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_roles(db_session)

    client.post(SIGNUP_URL, json=signup_payload())

    user = db_session.scalar(select(User).where(User.email == SIGNUP_EMAIL))
    assert user is not None
    assert user.role.name == "manufacturer_user"
