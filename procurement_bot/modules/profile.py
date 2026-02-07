"""Profile handling for local configuration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from .data_model import UserProfile
from .validators import validate_required_fields
from .storage import LocalStorage


class ProfileService:
    REQUIRED_FIELDS = [
        "company_name",
        "inn",
        "kpp",
        "ogrn",
        "bank_name",
        "bank_account",
        "correspondent_account",
        "bik",
        "address",
        "contact_person",
        "email",
        "phone",
        "keywords",
    ]

    def __init__(self, storage: LocalStorage) -> None:
        self.storage = storage

    def load_profile(self) -> UserProfile:
        payload = self.storage.read_json("config/profile.json")
        return UserProfile(**payload)

    def save_profile(self, profile: UserProfile) -> None:
        payload = asdict(profile)
        validate_required_fields(payload, self.REQUIRED_FIELDS)
        self.storage.write_json("config/profile.json", payload)

    def profile_summary(self, profile: UserProfile) -> Dict[str, str]:
        return {
            "Компания": profile.company_name,
            "ИНН": profile.inn,
            "Контакт": profile.contact_person,
            "Телефон": profile.phone,
            "Ключевые слова": ", ".join(profile.keywords),
        }
