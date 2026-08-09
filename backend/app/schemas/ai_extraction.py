from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SuggestionConfidence = Literal["high", "medium", "low"]
SuggestedValue = str | int | float | bool


class AiSuggestedValue(BaseModel):
    """One AI-proposed value with provenance for manufacturer review."""

    value: SuggestedValue
    confidence: SuggestionConfidence
    source: str | None = None


class AiFieldSuggestion(AiSuggestedValue):
    """A validated suggestion mapped to one template field."""

    field_code: str
    field_label: str


class AiIdentitySuggestions(BaseModel):
    """Optional suggestions for fixed product-item identity fields."""

    serial_number: AiSuggestedValue | None = None
    manufacture_date: AiSuggestedValue | None = None


class AiExtractionResponse(BaseModel):
    """Reviewable extraction result; this response never modifies an item."""

    identity: AiIdentitySuggestions = Field(default_factory=AiIdentitySuggestions)
    fields: list[AiFieldSuggestion] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
