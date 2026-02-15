"""Entry point for the procurement bot desktop app."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

from modules import (
    DesktopNotifier,
    DocumentPreparationService,
    LocalStorage,
    MonitoringScheduler,
    ProcurementApp,
    ProfileService,
    ReportService,
    TenderAnalysisService,
    TenderMonitor,
    TenderScraper,
)
from modules.ai_local import LocalAIAnalyzer
from modules.logging_config import setup_logging


def main() -> None:
    base_path = Path(__file__).resolve().parent
    setup_logging(base_path)
    storage = LocalStorage(base_path)
    notifier = DesktopNotifier()
    profile_service = ProfileService(storage)
    config = storage.read_json("config/platform_config.json")
    scraper = TenderScraper(result_limit=config.get("result_limit", 5))
    monitor = TenderMonitor(storage, notifier, scraper)
    analyzer = LocalAIAnalyzer()
    analysis_service = TenderAnalysisService(storage, analyzer)
    document_service = DocumentPreparationService(storage)
    report_service = ReportService(storage)

    root = tk.Tk()
    app = ProcurementApp(
        root,
        storage,
        profile_service,
        monitor,
        analysis_service,
        document_service,
        report_service,
    )

    scheduler = MonitoringScheduler(
        interval_minutes=config.get("search_interval_minutes", 60),
        callback=app.run_monitoring,
    )
    scheduler.start_tk(root)
    root.mainloop()
    scheduler.stop()


if __name__ == "__main__":
    main()
