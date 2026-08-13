from getpass import getpass
from secrets import compare_digest

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Organization, Role, User
from app.security import hash_password
from scripts.seed_reference_data import ORGANIZATION_NAME, ROLE_NAMES


MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role_name: str,
    organization_name: str | None = None,
) -> User:
    """Create one user without exposing or storing their plain password."""

    normalized_email = normalize_email(email)
    validate_password(password)

    if role_name not in ROLE_NAMES:
        raise ValueError(f"Role must be one of: {', '.join(ROLE_NAMES)}")

    existing_user = db.scalar(
        select(User).where(User.email == normalized_email),
    )
    if existing_user is not None:
        raise ValueError("A user with this email already exists")

    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise ValueError("Role not found; run the reference-data seed first")

    organization = None
    if role_name in {"manufacturer_user", "service_technician"}:
        if not organization_name:
            raise ValueError("Organization users require an organization")

        organization = db.scalar(
            select(Organization).where(Organization.name == organization_name),
        )
        if organization is None:
            raise ValueError(
                "Organization not found; run the reference-data seed first",
            )

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        status="active",
        role=role,
        organization=organization,
    )
    db.add(user)
    db.flush()
    return user


def normalize_email(email: str) -> str:
    """Normalize and perform basic validation of an account email."""

    normalized_email = email.strip().lower()
    local_part, separator, domain = normalized_email.partition("@")

    if (
        not separator
        or not local_part
        or not domain
        or "." not in domain
        or len(normalized_email) > 320
    ):
        raise ValueError("Enter a valid email address")

    return normalized_email


def validate_password(password: str) -> None:
    """Apply a small, passphrase-friendly password length policy."""

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must contain at least {MIN_PASSWORD_LENGTH} characters",
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must contain at most {MAX_PASSWORD_LENGTH} characters",
        )


def main() -> None:
    """Prompt for account details and create the user transactionally."""

    email = input("Email: ")
    role_name = input("Role [manufacturer_user]: ").strip() or "manufacturer_user"

    organization_name = None
    if role_name in {"manufacturer_user", "service_technician"}:
        organization_name = (
            input(f"Organization [{ORGANIZATION_NAME}]: ").strip()
            or ORGANIZATION_NAME
        )

    password = getpass("Password: ")
    password_confirmation = getpass("Confirm password: ")

    if not compare_digest(password, password_confirmation):
        raise SystemExit("Passwords do not match; no user was created.")

    try:
        with SessionLocal.begin() as db:
            user = create_user(
                db,
                email=email,
                password=password,
                role_name=role_name,
                organization_name=organization_name,
            )
            created_email = user.email
    except ValueError as error:
        raise SystemExit(f"User was not created: {error}") from error

    print(f"User {created_email} created successfully.")


if __name__ == "__main__":
    main()
