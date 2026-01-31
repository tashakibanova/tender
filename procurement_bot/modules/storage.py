"""Local storage utilities for JSON and report artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


class LocalStorage:
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.lots_path = base_path / "data" / "lots"
        self.reports_path = base_path / "data" / "reports"
        self.templates_path = base_path / "data" / "templates"
        self.config_path = base_path / "config"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for path in [self.lots_path, self.reports_path, self.templates_path]:
            path.mkdir(parents=True, exist_ok=True)

    def read_json(self, relative_path: str) -> Dict[str, Any]:
        path = self.base_path / relative_path
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, relative_path: str, payload: Dict[str, Any]) -> None:
        path = self.base_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def store_lot(self, lot: Any) -> Path:
        data = asdict(lot)
        file_path = self.lots_path / f"{data['lot_id']}.json"
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return file_path

    def list_lots(self) -> List[Dict[str, Any]]:
        lots = []
        for file_path in sorted(self.lots_path.glob("*.json")):
            lots.append(json.loads(file_path.read_text(encoding="utf-8")))
        return lots

    def update_search_history(self, query: str) -> None:
        history = self.read_json("config/search_history.json") or {"history": []}
        history["history"].append(query)
        self.write_json("config/search_history.json", history)

    def store_report(self, report_name: str, payload: Iterable[Dict[str, Any]]) -> Path:
        report_path = self.reports_path / report_name
        report_path.write_text(
            json.dumps(list(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return report_path
