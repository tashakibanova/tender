"""Validation helpers to enforce required data."""

from typing import Dict, Iterable


def validate_required_fields(payload: Dict[str, object], required: Iterable[str]) -> None:
    missing = [field for field in required if not payload.get(field)]
    if missing:
        fields = ", ".join(missing)
        raise ValueError(f"Не заполнены обязательные поля: {fields}")
