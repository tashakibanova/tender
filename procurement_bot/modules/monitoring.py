"""Monitoring module that searches tenders through browser UI automation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Iterable, List

from .data_model import LotRecord
from .notifications import DesktopNotifier
from .scraping import TenderScraper
from .storage import LocalStorage


class TenderMonitor:
    def __init__(
        self,
        storage: LocalStorage,
        notifier: DesktopNotifier,
        scraper: TenderScraper,
    ) -> None:
        self.storage = storage
        self.notifier = notifier
        self.scraper = scraper

    def search_lots(self, keywords: Iterable[str], platform: dict) -> List[LotRecord]:
        results = []
        for keyword in keywords:
            scraped_lots = self.scraper.search_platform(platform, keyword)
            for scraped in scraped_lots:
                lot_id = self._build_lot_id(scraped["url"], scraped["title"])
                lot = LotRecord(
                    lot_id=lot_id,
                    title=scraped["title"],
                    platform=platform.get("name", ""),
                    url=scraped["url"],
                    published_at=scraped.get("published_at", datetime.now().isoformat()),
                )
                results.append(lot)
                self.storage.store_lot(lot)
        if results:
            self.notifier.notify_new_lots(len(results))
        return results

    def run_monitoring_cycle(self, keywords: Iterable[str]) -> List[LotRecord]:
        config = self.storage.read_json("config/platform_config.json")
        platforms = [p for p in config.get("platforms", []) if p.get("enabled")]
        all_lots: List[LotRecord] = []
        for platform in platforms:
            all_lots.extend(self.search_lots(keywords, platform))
        for keyword in keywords:
            self.storage.update_search_history(keyword)
        return all_lots

    def _build_lot_id(self, url: str, title: str) -> str:
        namespace = uuid.NAMESPACE_URL
        return str(uuid.uuid5(namespace, f"{url}-{title}"))
