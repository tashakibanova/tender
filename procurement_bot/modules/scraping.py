"""Browser scraping helpers for tender platforms."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By


@dataclass
class ScrapedLot:
    title: str
    url: str
    published_at: Optional[str] = None


class TenderScraper:
    def __init__(self, result_limit: int = 5) -> None:
        self.result_limit = result_limit
        self.logger = logging.getLogger(__name__)

    def search_platform(self, platform: Dict[str, object], keyword: str) -> List[Dict[str, str]]:
        engine = (platform.get("engine") or "playwright").lower()
        search_url = self._build_search_url(platform, keyword)
        if engine == "selenium":
            lots = self._search_with_selenium(search_url)
        else:
            lots = self._search_with_playwright(search_url)
        return [lot.__dict__ for lot in lots]

    def _build_search_url(self, platform: Dict[str, object], keyword: str) -> str:
        base_url = str(platform.get("search_url", ""))
        path = str(platform.get("search_path", ""))
        if "{query}" in path:
            query = quote_plus(keyword)
            return urljoin(base_url, path.format(query=query))
        return f"{base_url}?searchString={quote_plus(keyword)}"

    def _search_with_playwright(self, url: str) -> List[ScrapedLot]:
        lots: List[ScrapedLot] = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded")
                self._wait_for_results(page)
                elements = self._collect_result_elements_playwright(page)
                for element in elements[: self.result_limit]:
                    lot = self._extract_lot_from_element_playwright(element)
                    if lot:
                        lots.append(lot)
                context.close()
                browser.close()
        except Exception as exc:
            self.logger.exception("Playwright scraping failed for %s", url, exc_info=exc)
        return lots

    def _wait_for_results(self, page) -> None:
        selectors = [
            "div.search-registry-entry-block",
            "div.registry-entry__body",
            "div.search-results__item",
            "a[href*='purchase']",
        ]
        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=5000)
                return
            except PlaywrightTimeoutError:
                continue

    def _collect_result_elements_playwright(self, page) -> List[object]:
        selectors = [
            "div.search-registry-entry-block",
            "div.registry-entry__body",
            "div.search-results__item",
        ]
        for selector in selectors:
            elements = page.query_selector_all(selector)
            if elements:
                return elements
        return []

    def _extract_lot_from_element_playwright(self, element) -> Optional[ScrapedLot]:
        link = element.query_selector("a[href]")
        if not link:
            return None
        title = (link.inner_text() or "").strip()
        href = link.get_attribute("href") or ""
        url = href if href.startswith("http") else f"https://zakupki.gov.ru{href}"
        published_at = None
        date_selectors = [
            "div.registry-entry__header-top__date",
            "span.data-block__value",
            "span.search-results__date",
        ]
        for selector in date_selectors:
            node = element.query_selector(selector)
            if node:
                published_at = (node.inner_text() or "").strip()
                break
        if not title:
            title = (element.inner_text() or "").split("\n")[0].strip()
        return ScrapedLot(title=title, url=url, published_at=published_at)

    def _search_with_selenium(self, url: str) -> List[ScrapedLot]:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = None
        lots: List[ScrapedLot] = []
        try:
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            elements = self._collect_result_elements_selenium(driver)
            for element in elements[: self.result_limit]:
                lot = self._extract_lot_from_element_selenium(element)
                if lot:
                    lots.append(lot)
        except WebDriverException as exc:
            self.logger.exception("Selenium scraping failed for %s", url, exc_info=exc)
            return []
        finally:
            if driver:
                driver.quit()
        return lots

    def _collect_result_elements_selenium(self, driver) -> List[object]:
        selectors = [
            "div.search-registry-entry-block",
            "div.registry-entry__body",
            "div.search-results__item",
        ]
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements
        return []

    def _extract_lot_from_element_selenium(self, element) -> Optional[ScrapedLot]:
        links = element.find_elements(By.CSS_SELECTOR, "a[href]")
        if not links:
            return None
        link = links[0]
        title = link.text.strip()
        href = link.get_attribute("href") or ""
        url = href if href.startswith("http") else f"https://zakupki.gov.ru{href}"
        published_at = None
        for selector in [
            "div.registry-entry__header-top__date",
            "span.data-block__value",
            "span.search-results__date",
        ]:
            nodes = element.find_elements(By.CSS_SELECTOR, selector)
            if nodes:
                published_at = nodes[0].text.strip()
                break
        if not title:
            title = element.text.split("\n")[0].strip()
        return ScrapedLot(title=title, url=url, published_at=published_at)
