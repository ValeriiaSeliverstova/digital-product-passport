from typing import Literal

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """OAuth2 access token returned after successful login."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
