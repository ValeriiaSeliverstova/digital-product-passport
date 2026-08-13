import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_reject_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(
            _env_file=None,
            postgres_db="test",
            postgres_user="test",
            postgres_password="test",
            jwt_secret_key="change_me",
        )


def test_settings_reject_frontend_url_with_path() -> None:
    with pytest.raises(ValidationError, match="without a path"):
        Settings(
            _env_file=None,
            postgres_db="test",
            postgres_user="test",
            postgres_password="test",
            jwt_secret_key="test-only-secret-that-is-at-least-32-characters",
            frontend_origin="http://localhost:5173/application",
        )


def test_settings_reject_non_azure_support_project_url() -> None:
    with pytest.raises(ValidationError, match="dev.azure.com project URL"):
        Settings(
            _env_file=None,
            postgres_db="test",
            postgres_user="test",
            postgres_password="test",
            jwt_secret_key="test-only-secret-that-is-at-least-32-characters",
            azure_devops_project_url="https://example.com/what-software/Students",
        )


def test_settings_treat_empty_azure_pat_as_unconfigured() -> None:
    test_settings = Settings(
        _env_file=None,
        postgres_db="test",
        postgres_user="test",
        postgres_password="test",
        jwt_secret_key="test-only-secret-that-is-at-least-32-characters",
        azure_devops_pat="  ",
    )

    assert test_settings.azure_devops_pat is None
