from datetime import date
from math import isfinite
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


FieldDataType = Literal["text", "integer", "decimal", "boolean", "date"]
FieldAccessLevel = Literal["public", "manufacturer"]

ALLOWED_RULES = {
    "text": {"min_length", "max_length", "allowed_values"},
    "integer": {"min", "max"},
    "decimal": {"min", "max"},
    "boolean": set(),
    "date": {"min", "max"},
}


class TemplateFieldData(BaseModel):
    """Validated values used to create or fully update a template field."""

    code: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    label: str = Field(min_length=1, max_length=255)
    data_type: FieldDataType
    is_required: bool = False
    display_order: int = Field(default=0, ge=0, le=1_000_000)
    access_level: FieldAccessLevel = "public"
    validation_rules: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @model_validator(mode="after")
    def validate_rules(self) -> "TemplateFieldData":
        """Ensure rules match the selected field type."""

        unknown_rules = set(self.validation_rules) - ALLOWED_RULES[self.data_type]
        if unknown_rules:
            names = ", ".join(sorted(unknown_rules))
            raise ValueError(f"Unsupported validation rules: {names}")

        if self.data_type == "text":
            validate_text_rules(self.validation_rules)
        elif self.data_type in {"integer", "decimal"}:
            validate_number_rules(self.data_type, self.validation_rules)
        elif self.data_type == "date":
            validate_date_rules(self.validation_rules)

        return self


class TemplateFieldCreate(TemplateFieldData):
    """Request body for adding a field to a template."""


# A template may receive several fields in one request, but the limit keeps
# accidental or abusive requests from becoming unnecessarily large.
TemplateFieldCreateList = Annotated[
    list[TemplateFieldCreate],
    Field(min_length=1, max_length=100),
]


class TemplateFieldUpdate(TemplateFieldData):
    """Request body for replacing an existing template field definition."""


class TemplateFieldResponse(TemplateFieldData):
    """Template field data returned by the API."""

    id: UUID
    template_id: UUID

    model_config = ConfigDict(from_attributes=True)


def validate_text_rules(rules: dict[str, Any]) -> None:
    """Validate length and choice rules for text fields."""

    minimum = rules.get("min_length")
    maximum = rules.get("max_length")

    for name, value in (("min_length", minimum), ("max_length", maximum)):
        if value is not None and (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 0 <= value <= 10_000
        ):
            raise ValueError(f"{name} must be an integer from 0 to 10000")

    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("min_length cannot be greater than max_length")

    allowed_values = rules.get("allowed_values")
    if allowed_values is None:
        return

    if (
        not isinstance(allowed_values, list)
        or not 1 <= len(allowed_values) <= 100
        or any(
            not isinstance(value, str) or not value.strip() or len(value) > 255
            for value in allowed_values
        )
    ):
        raise ValueError(
            "allowed_values must contain 1 to 100 non-empty strings",
        )

    if len(allowed_values) != len(set(allowed_values)):
        raise ValueError("allowed_values cannot contain duplicates")


def validate_number_rules(
    data_type: str,
    rules: dict[str, Any],
) -> None:
    """Validate numeric minimum and maximum rules."""

    minimum = rules.get("min")
    maximum = rules.get("max")

    for name, value in (("min", minimum), ("max", maximum)):
        if value is None:
            continue
        is_valid_number = isinstance(value, (int, float)) and not isinstance(
            value,
            bool,
        )
        if (
            not is_valid_number
            or (isinstance(value, float) and not isfinite(value))
            or abs(value) > 1_000_000_000_000_000
        ):
            raise ValueError(
                f"{name} must be a finite number between -1e15 and 1e15",
            )
        if data_type == "integer" and not isinstance(value, int):
            raise ValueError(f"{name} must be an integer for integer fields")

    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("min cannot be greater than max")


def validate_date_rules(rules: dict[str, Any]) -> None:
    """Validate ISO date boundaries."""

    parsed_dates: dict[str, date] = {}
    for name in ("min", "max"):
        value = rules.get(name)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"{name} must use YYYY-MM-DD format")
        try:
            parsed_dates[name] = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{name} must use YYYY-MM-DD format") from error

    if (
        "min" in parsed_dates
        and "max" in parsed_dates
        and parsed_dates["min"] > parsed_dates["max"]
    ):
        raise ValueError("min date cannot be later than max date")
