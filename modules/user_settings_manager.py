"""UserSettingsManager: управление персональными настройками пользователя."""

from __future__ import annotations

import json
import os


class UserSettingsManager:
    """Управление пользовательскими настройками в рамках организации."""

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    ORGANIZATIONS_DIR = os.path.join(BASE_DIR, "organizations")
    SETTINGS_FILE = "settings.json"

    @classmethod
    def load_settings(cls, inn: str) -> dict:
        """Загружает настройки для указанного ИНН, создавая файл при необходимости."""
        cls._ensure_org_dir(inn)
        settings_path = cls._settings_path(inn)
        if not os.path.exists(settings_path):
            settings = cls._default_settings()
            cls.save_settings(inn, settings)
            return settings
        with open(settings_path, "r", encoding="utf-8") as file:
            settings = json.load(file)
        validated = cls._validate_settings(settings)
        cls.save_settings(inn, validated)
        return validated

    @classmethod
    def save_settings(cls, inn: str, settings: dict) -> None:
        """Сохраняет обновленные настройки для указанного ИНН."""
        cls._ensure_org_dir(inn)
        validated = cls._validate_settings(settings)
        with open(cls._settings_path(inn), "w", encoding="utf-8") as file:
            json.dump(validated, file, ensure_ascii=False, indent=2)

    @classmethod
    def reset_to_defaults(cls, inn: str) -> dict:
        """Сбрасывает настройки к значениям по умолчанию."""
        defaults = cls._default_settings()
        cls.save_settings(inn, defaults)
        return defaults

    @classmethod
    def _settings_path(cls, inn: str) -> str:
        return os.path.join(cls.ORGANIZATIONS_DIR, inn, cls.SETTINGS_FILE)

    @classmethod
    def _ensure_org_dir(cls, inn: str) -> None:
        os.makedirs(os.path.join(cls.ORGANIZATIONS_DIR, inn), exist_ok=True)

    @classmethod
    def _default_settings(cls) -> dict:
        return {
            "monitoring_preferences": {
                "check_interval_minutes": 30,
                "search_depth_days": 30,
                "auto_update_keywords": True,
                "active_platforms": [],
            },
            "financial_parameters": {
                "default_cost_items": [],
                "min_profitability_threshold": 10.0,
                "tax_system": "УСН 6%",
            },
            "system_behavior": {
                "notifications": ["popup"],
                "require_confirmation": {
                    "before_submitting_application": True,
                    "before_deleting_archive": True,
                    "before_applying_keyword_suggestions": True,
                },
            },
            "integrations_and_export": {
                "templates_path": "../templates/",
                "report_format": "excel",
                "browser_headless_mode": False,
                "preferred_price_format": "xlsx",
            },
        }

    @classmethod
    def _validate_settings(cls, settings: dict) -> dict:
        defaults = cls._default_settings()
        merged = cls._merge_settings(defaults, settings)

        monitoring = merged["monitoring_preferences"]
        monitoring["check_interval_minutes"] = cls._validate_int_range(
            monitoring.get("check_interval_minutes"), 5, 1440, 30
        )
        monitoring["search_depth_days"] = cls._validate_int_range(
            monitoring.get("search_depth_days"), 1, 365, 30
        )
        monitoring["auto_update_keywords"] = bool(monitoring.get("auto_update_keywords", True))
        monitoring["active_platforms"] = cls._validate_list(monitoring.get("active_platforms", []))

        financial = merged["financial_parameters"]
        financial["default_cost_items"] = cls._validate_cost_items(
            financial.get("default_cost_items", [])
        )
        financial["min_profitability_threshold"] = cls._validate_float(
            financial.get("min_profitability_threshold"), 10.0
        )
        financial["tax_system"] = cls._validate_choice(
            financial.get("tax_system"),
            ["УСН 6%", "УСН 15%", "ОСНО"],
            "УСН 6%",
        )

        behavior = merged["system_behavior"]
        behavior["notifications"] = cls._validate_choice_list(
            behavior.get("notifications", ["popup"]),
            ["popup", "sound", "email", "telegram"],
        )
        require_confirm = behavior.get("require_confirmation", {})
        behavior["require_confirmation"] = {
            "before_submitting_application": bool(
                require_confirm.get("before_submitting_application", True)
            ),
            "before_deleting_archive": bool(
                require_confirm.get("before_deleting_archive", True)
            ),
            "before_applying_keyword_suggestions": bool(
                require_confirm.get("before_applying_keyword_suggestions", True)
            ),
        }

        integrations = merged["integrations_and_export"]
        integrations["templates_path"] = str(integrations.get("templates_path", "../templates/"))
        integrations["report_format"] = cls._validate_choice(
            integrations.get("report_format"), ["excel", "pdf"], "excel"
        )
        integrations["browser_headless_mode"] = bool(
            integrations.get("browser_headless_mode", False)
        )
        integrations["preferred_price_format"] = cls._validate_choice(
            integrations.get("preferred_price_format"), ["xlsx", "csv"], "xlsx"
        )

        return merged

    @classmethod
    def _merge_settings(cls, defaults: dict, settings: dict) -> dict:
        merged = {}
        for key, value in defaults.items():
            if isinstance(value, dict):
                merged[key] = cls._merge_settings(value, settings.get(key, {}))
            else:
                merged[key] = settings.get(key, value)
        return merged

    @staticmethod
    def _validate_int_range(value, min_value: int, max_value: int, fallback: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return fallback
        if number < min_value or number > max_value:
            return fallback
        return number

    @staticmethod
    def _validate_float(value, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _validate_choice(value, options: list[str], fallback: str) -> str:
        return value if value in options else fallback

    @staticmethod
    def _validate_choice_list(value, options: list[str]) -> list[str]:
        if not isinstance(value, list):
            return [options[0]]
        return [item for item in value if item in options] or [options[0]]

    @staticmethod
    def _validate_list(value) -> list:
        if isinstance(value, list):
            return value
        return []

    @staticmethod
    def _validate_cost_items(items) -> list[dict]:
        if not isinstance(items, list):
            return []
        validated = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            item_type = item.get("type")
            value = item.get("value")
            if not name or item_type not in {"percent", "fixed"}:
                continue
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            validated.append({"name": name, "type": item_type, "value": value})
        return validated
