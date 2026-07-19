from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductCategoryResponse(BaseModel):
    """Category data returned by the API."""

    id: UUID
    parent_category_id: UUID | None
    code: str
    name: str
    is_active: bool

    # Allow Pydantic to create responses from SQLAlchemy model objects.
    model_config = ConfigDict(from_attributes=True)
