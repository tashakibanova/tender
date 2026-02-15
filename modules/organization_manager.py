"""OrganizationManager: управление профилями организаций."""

from __future__ import annotations

import json
import os
import shutil
from datetime import date, datetime


class OrganizationManager:
    """Управление профилями организаций и их документами."""

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    ORGANIZATIONS_DIR = os.path.join(BASE_DIR, "organizations")

    BASIC_FIELDS = [
        "name",
        "registration_date",
        "legal_address",
        "postal_address",
        "actual_address",
        "director_full_name",
        "director_position",
        "phones",
        "fax",
        "email",
        "website",
        "inn",
        "kpp",
        "bank_details",
        "founders",
        "branches",
        "egrul_info",
        "responsible_person",
        "deal_approval_info",
    ]

    @classmethod
    def create_profile(cls, profile_data: dict | None = None) -> str:
        """Создает профиль организации и структуру папок.

        profile_data может содержать ключи: basic_info, classifiers, custom_fields.
        Если данные отсутствуют, используются значения по умолчанию "нет".
        """
        os.makedirs(cls.ORGANIZATIONS_DIR, exist_ok=True)
        profile = cls._build_profile(profile_data)
        inn = profile["basic_info"].get("inn", "нет") or "нет"
        org_path = os.path.join(cls.ORGANIZATIONS_DIR, inn)
        if os.path.exists(org_path):
            raise ValueError("Организация с таким ИНН уже существует.")
        os.makedirs(os.path.join(org_path, "docs"), exist_ok=True)
        os.makedirs(os.path.join(org_path, "archive_docs"), exist_ok=True)
        cls._write_profile(org_path, profile)
        cls._write_registry(org_path, [])
        return org_path

    @classmethod
    def get_profile(cls, inn: str) -> dict:
        """Возвращает полный профиль организации по ИНН."""
        profile_path = os.path.join(cls.ORGANIZATIONS_DIR, inn, "profile.json")
        if not os.path.exists(profile_path):
            raise FileNotFoundError("Профиль организации не найден.")
        with open(profile_path, "r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    def list_organizations(cls) -> list[str]:
        """Возвращает список всех ИНН организаций."""
        if not os.path.exists(cls.ORGANIZATIONS_DIR):
            return []
        inns: list[str] = []
        for entry in os.listdir(cls.ORGANIZATIONS_DIR):
            org_dir = os.path.join(cls.ORGANIZATIONS_DIR, entry)
            if os.path.isdir(org_dir) and os.path.exists(os.path.join(org_dir, "profile.json")):
                inns.append(entry)
        return sorted(inns)

    @classmethod
    def add_document(
        cls,
        inn: str,
        source_path: str,
        document_name: str,
        expires_at: str | None = None,
    ) -> dict:
        """Добавляет документ в профиль организации и обновляет реестр."""
        org_dir = os.path.join(cls.ORGANIZATIONS_DIR, inn)
        if not os.path.exists(org_dir):
            raise FileNotFoundError("Организация не найдена.")
        docs_dir = os.path.join(org_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        file_name = os.path.basename(source_path)
        target = os.path.join(docs_dir, file_name)
        shutil.copy2(source_path, target)
        registry = cls._read_registry(org_dir)
        record = {
            "file_name": file_name,
            "document_name": document_name,
            "expires_at": expires_at,
            "added_at": datetime.now().strftime("%Y-%m-%d"),
            "status": "active",
        }
        registry.append(record)
        cls._write_registry(org_dir, registry)
        return record

    @classmethod
    def check_document_expirations(cls) -> None:
        """Проверяет сроки документов и переносит просроченные в архив."""
        today = date.today()
        for inn in cls.list_organizations():
            org_dir = os.path.join(cls.ORGANIZATIONS_DIR, inn)
            registry = cls._read_registry(org_dir)
            updated = False
            for record in registry:
                expires_at = record.get("expires_at")
                if not expires_at:
                    continue
                try:
                    expiry = datetime.strptime(expires_at, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if expiry <= today and record.get("status") != "archived":
                    cls._archive_document(org_dir, record.get("file_name"))
                    record["status"] = "archived"
                    updated = True
            if updated:
                cls._write_registry(org_dir, registry)

    @classmethod
    def add_custom_field(cls, inn: str, key: str, value: str) -> None:
        """Добавляет произвольное поле в профиль организации."""
        profile = cls.get_profile(inn)
        profile.setdefault("custom_fields", {})
        profile["custom_fields"][key] = value
        cls._write_profile(os.path.join(cls.ORGANIZATIONS_DIR, inn), profile)

    @classmethod
    def _build_profile(cls, profile_data: dict | None) -> dict:
        basic_info = {field: "нет" for field in cls.BASIC_FIELDS}
        classifiers = {
            "okved": [],
            "okpo": "нет",
            "okogu": "нет",
            "oktmo": "нет",
            "kpp": "нет",
        }
        custom_fields: dict = {}
        if profile_data:
            basic_info.update(profile_data.get("basic_info", {}))
            classifiers.update(profile_data.get("classifiers", {}))
            custom_fields.update(profile_data.get("custom_fields", {}))
        basic_info = {k: (v if v not in [None, ""] else "нет") for k, v in basic_info.items()}
        classifiers = {k: (v if v not in [None, ""] else "нет") for k, v in classifiers.items()}
        if not isinstance(classifiers.get("okved"), list):
            classifiers["okved"] = [str(classifiers["okved"])]
        return {
            "basic_info": basic_info,
            "classifiers": classifiers,
            "custom_fields": custom_fields,
        }

    @classmethod
    def _write_profile(cls, org_path: str, profile: dict) -> None:
        profile_path = os.path.join(org_path, "profile.json")
        with open(profile_path, "w", encoding="utf-8") as file:
            json.dump(profile, file, ensure_ascii=False, indent=2)

    @classmethod
    def _read_registry(cls, org_path: str) -> list[dict]:
        registry_path = os.path.join(org_path, "documents_registry.json")
        if not os.path.exists(registry_path):
            return []
        with open(registry_path, "r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    def _write_registry(cls, org_path: str, registry: list[dict]) -> None:
        registry_path = os.path.join(org_path, "documents_registry.json")
        with open(registry_path, "w", encoding="utf-8") as file:
            json.dump(registry, file, ensure_ascii=False, indent=2)

    @classmethod
    def _archive_document(cls, org_path: str, file_name: str | None) -> None:
        if not file_name:
            return
        source = os.path.join(org_path, "docs", file_name)
        target = os.path.join(org_path, "archive_docs", file_name)
        if os.path.exists(source):
            shutil.move(source, target)
