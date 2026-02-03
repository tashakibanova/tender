"""Reporting module for exporting lots to Excel/JSON."""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict

import pandas as pd

from .storage import LocalStorage


class ReportService:
    def __init__(self, storage: LocalStorage) -> None:
        self.storage = storage

    def export_lots_to_excel(self, report_name: str = "lots_report.xlsx") -> Path:
        lots = self.storage.list_lots()
        df = pd.DataFrame(lots)
        report_path = self.storage.reports_path / report_name
        df.to_excel(report_path, index=False)
        return report_path

    def export_lots_to_json(self, report_name: str = "lots_report.json") -> Path:
        lots = self.storage.list_lots()
        return self.storage.store_report(report_name, lots)
