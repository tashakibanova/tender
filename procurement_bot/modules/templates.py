"""Template utilities for document placeholders."""

from __future__ import annotations

from typing import Dict


def build_template_payload(profile: Dict[str, str], price: str) -> Dict[str, str]:
    return {
        "НАИМЕНОВАНИЕ": profile.get("company_name", ""),
        "ИНН": profile.get("inn", ""),
        "ЦЕНА": price,
    }
