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
