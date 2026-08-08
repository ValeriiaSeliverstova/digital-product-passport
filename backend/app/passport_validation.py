from datetime import date
from math import isfinite
from typing import Any

from app.models import TemplateField


def validate_passport_data(
    passport_data: dict[str, Any],
    fields: list[TemplateField],
    *,
    require_complete: bool,
) -> None:
    """Validate product values against one exact template version."""

    fields_by_code = {field.code: field for field in fields}
    unknown_codes = sorted(set(passport_data) - set(fields_by_code))
    if unknown_codes:
        raise ValueError(f"Unknown passport field: {unknown_codes[0]}")

    if require_complete:
        missing_codes = sorted(
            field.code
            for field in fields
            if field.is_required and passport_data.get(field.code) is None
        )
        if missing_codes:
            raise ValueError(
                f"Required passport field is missing: {missing_codes[0]}",
            )

    for code, value in passport_data.items():
        field = fields_by_code[code]
        if value is None and not field.is_required:
            continue
        validate_field_value(field, value)


def validate_field_value(field: TemplateField, value: Any) -> None:
    """Validate one value's type and configured rules."""

    if field.data_type == "text":
        if not isinstance(value, str):
            raise field_error(field, "must be text")
        if len(value) > 10_000:
            raise field_error(field, "must have at most 10000 characters")
        validate_text_value(field, value)
    elif field.data_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise field_error(field, "must be an integer")
        validate_number_value(field, value)
    elif field.data_type == "decimal":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise field_error(field, "must be a number")
        if isinstance(value, float) and not isfinite(value):
            raise field_error(field, "must be a finite number")
        validate_number_value(field, value)
    elif field.data_type == "boolean":
        if not isinstance(value, bool):
            raise field_error(field, "must be true or false")
    elif field.data_type == "date":
        if not isinstance(value, str):
            raise field_error(field, "must use YYYY-MM-DD format")
        try:
            parsed_value = date.fromisoformat(value)
        except ValueError as error:
            raise field_error(field, "must use YYYY-MM-DD format") from error
        validate_date_value(field, parsed_value)


def validate_text_value(field: TemplateField, value: str) -> None:
    rules = field.validation_rules
    if "min_length" in rules and len(value) < rules["min_length"]:
        raise field_error(
            field,
            f"must have at least {rules['min_length']} characters",
        )
    if "max_length" in rules and len(value) > rules["max_length"]:
        raise field_error(
            field,
            f"must have at most {rules['max_length']} characters",
        )
    if "allowed_values" in rules and value not in rules["allowed_values"]:
        raise field_error(field, "has a value that is not allowed")


def validate_number_value(field: TemplateField, value: int | float) -> None:
    rules = field.validation_rules
    if abs(value) > 1_000_000_000_000_000:
        raise field_error(field, "must be between -1e15 and 1e15")
    if "min" in rules and value < rules["min"]:
        raise field_error(field, f"must be at least {rules['min']}")
    if "max" in rules and value > rules["max"]:
        raise field_error(field, f"must be at most {rules['max']}")


def validate_date_value(field: TemplateField, value: date) -> None:
    rules = field.validation_rules
    if "min" in rules and value < date.fromisoformat(rules["min"]):
        raise field_error(field, f"must be on or after {rules['min']}")
    if "max" in rules and value > date.fromisoformat(rules["max"]):
        raise field_error(field, f"must be on or before {rules['max']}")


def field_error(field: TemplateField, message: str) -> ValueError:
    """Create a readable validation error without exposing internal details."""

    return ValueError(f"Passport field '{field.code}' {message}")
