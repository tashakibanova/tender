"""Security guidelines enforcing local-only actions."""

from __future__ import annotations


def ensure_local_only(action: str) -> None:
    if action in {"sign", "submit", "payment"}:
        raise ValueError("Автоматические подписи, платежи и подачи запрещены")
