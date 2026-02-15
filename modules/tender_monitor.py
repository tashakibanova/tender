"""TenderMonitor: поиск и фильтрация закупок с учетом параметров и профиля."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime


class TenderMonitor:
    """Управляет параметрами поиска и фильтрацией закупок."""

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    ORGANIZATIONS_DIR = os.path.join(BASE_DIR, "organizations")

    SEARCH_PARAMS_FILE = "search_parameters.json"
    PROFILE_FILE = "profile.json"
    LOTS_DIR = "lots"
    REGISTRY_FILE = "registry.json"
    INCOMING_FILE = "incoming_tenders.json"

    @classmethod
    def load_search_params(cls, inn: str) -> dict:
        """Загружает параметры поиска или создает файл с умолчаниями."""
        org_dir = cls._org_dir(inn)
        os.makedirs(org_dir, exist_ok=True)
        params_path = os.path.join(org_dir, cls.SEARCH_PARAMS_FILE)
        if not os.path.exists(params_path):
            params = cls._default_search_params()
            cls.save_search_params(inn, params)
            return params
        with open(params_path, "r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    def save_search_params(cls, inn: str, params: dict) -> None:
        """Сохраняет параметры поиска для организации."""
        org_dir = cls._org_dir(inn)
        os.makedirs(org_dir, exist_ok=True)
        params_path = os.path.join(org_dir, cls.SEARCH_PARAMS_FILE)
        with open(params_path, "w", encoding="utf-8") as file:
            json.dump(params, file, ensure_ascii=False, indent=2)

    @classmethod
    def open_search_params_editor(cls) -> None:
        """Открывает файл параметров поиска для ручного редактирования."""
        params_path = os.path.join(cls.BASE_DIR, cls.SEARCH_PARAMS_FILE)
        if not os.path.exists(params_path):
            with open(params_path, "w", encoding="utf-8") as file:
                json.dump(cls._default_search_params(), file, ensure_ascii=False, indent=2)
        cls._open_file(params_path)

    @classmethod
    def find_new_tenders(cls, inn: str) -> list[dict]:
        """Имитирует поиск лотов: фильтрует входящие и сохраняет в реестр."""
        search_params = cls.load_search_params(inn)
        profile = cls._load_profile(inn)
        candidates = cls._load_candidate_tenders(inn)
        filtered = cls.filter_tenders(candidates, search_params, datetime.now(), profile)
        saved = cls._save_registry(inn, filtered)
        return saved

    @classmethod
    def filter_tenders(
        cls,
        tenders: list,
        search_params: dict,
        current_time: datetime,
        profile: dict | None = None,
    ) -> list:
        """Фильтрует список закупок по параметрам поиска и профилю."""
        profile = profile or {}
        okved_terms = cls._profile_okved_terms(profile)
        terms = set(search_params.get("tools_and_terms", [])) | set(okved_terms)
        search_modes = search_params.get("search_modes", [])
        regions = set(search_params.get("regions", []))
        categories = set(search_params.get("categories", []))
        stages = set(search_params.get("stages", []))
        platforms = set(search_params.get("platforms", []))

        filtered = []
        for tender in tenders:
            if cls._is_expired(tender, current_time):
                continue
            if regions and tender.get("region") not in regions:
                continue
            if categories and tender.get("category") not in categories:
                continue
            if stages and tender.get("stage") not in stages:
                continue
            if platforms and tender.get("platform") not in platforms:
                continue
            description = tender.get("description", "") or ""
            if not cls._matches_terms(description, terms, search_modes):
                continue
            filtered.append(tender)
        return filtered

    @classmethod
    def _default_search_params(cls) -> dict:
        return {
            "tools_and_terms": [],
            "search_modes": [],
            "regions": [],
            "categories": [],
            "stages": [],
            "platforms": [],
        }

    @classmethod
    def _load_profile(cls, inn: str) -> dict:
        profile_path = os.path.join(cls._org_dir(inn), cls.PROFILE_FILE)
        if not os.path.exists(profile_path):
            return {}
        with open(profile_path, "r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    def _profile_okved_terms(cls, profile: dict) -> list[str]:
        classifiers = profile.get("classifiers", {}) if isinstance(profile, dict) else {}
        okved = classifiers.get("okved", [])
        if isinstance(okved, list):
            return [str(item) for item in okved]
        if okved:
            return [str(okved)]
        return []

    @classmethod
    def _load_candidate_tenders(cls, inn: str) -> list[dict]:
        incoming_path = os.path.join(cls._org_dir(inn), cls.INCOMING_FILE)
        if not os.path.exists(incoming_path):
            return []
        with open(incoming_path, "r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    def _save_registry(cls, inn: str, tenders: list[dict]) -> list[dict]:
        lots_dir = os.path.join(cls._org_dir(inn), cls.LOTS_DIR)
        os.makedirs(lots_dir, exist_ok=True)
        registry_path = os.path.join(lots_dir, cls.REGISTRY_FILE)
        existing = []
        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as file:
                existing = json.load(file)
        existing_ids = {item.get("number") for item in existing}
        new_records = []
        for tender in tenders:
            if tender.get("number") in existing_ids:
                continue
            record = {
                "number": tender.get("number"),
                "title": tender.get("title"),
                "price": tender.get("price"),
                "deadline": tender.get("deadline"),
                "url": tender.get("url"),
                "platform": tender.get("platform"),
                "status": tender.get("status", "новый"),
            }
            new_records.append(record)
        all_records = existing + new_records
        with open(registry_path, "w", encoding="utf-8") as file:
            json.dump(all_records, file, ensure_ascii=False, indent=2)
        return all_records

    @classmethod
    def _is_expired(cls, tender: dict, current_time: datetime) -> bool:
        deadline = tender.get("deadline")
        if not deadline:
            return False
        try:
            end_time = datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            return False
        return end_time <= current_time

    @classmethod
    def _matches_terms(cls, text: str, terms: set, search_modes: list) -> bool:
        if not terms and not search_modes:
            return True
        lowered = text.lower()
        for term in terms:
            if term and term.lower() in lowered:
                return True
        for mode in search_modes:
            term = mode.get("term", "")
            mode_type = mode.get("mode", "")
            if mode_type == "exact_in_text":
                if term.lower() in lowered:
                    return True
            elif mode_type == "nearby_words":
                distance = int(mode.get("distance", 1))
                if cls._nearby_words(lowered, term, distance):
                    return True
            elif mode_type == "any_ending":
                if cls._any_ending_match(lowered, term):
                    return True
        return False

    @staticmethod
    def _nearby_words(text: str, term: str, distance: int) -> bool:
        words = re.findall(r"\w+", text.lower())
        target = term.lower().split()
        if not target or not words:
            return False
        for i in range(len(words)):
            window = words[i : i + distance + len(target)]
            if all(word in window for word in target):
                return True
        return False

    @staticmethod
    def _any_ending_match(text: str, term: str) -> bool:
        if not term:
            return False
        normalized = term.lower()[:-1]
        return normalized in text.lower()

    @classmethod
    def _org_dir(cls, inn: str) -> str:
        return os.path.join(cls.ORGANIZATIONS_DIR, inn)

    @staticmethod
    def _open_file(path: str) -> None:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif os.name == "posix":
            os.system(f'xdg-open "{path}"')
