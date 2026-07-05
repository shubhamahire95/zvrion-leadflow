"""Generic Google Maps scraper implemented with Playwright."""
from __future__ import annotations
import logging, re
from collections.abc import Callable
from urllib.parse import quote_plus
from playwright.sync_api import TimeoutError as PlaywrightTimeout, sync_playwright
from config import NAVIGATION_TIMEOUT_MS, SCROLL_ROUNDS

LOG = logging.getLogger(__name__)
StatusCallback = Callable[..., None]

class GoogleMapsScraper:
    def __init__(self, headless: bool = True, timeout_ms: int = NAVIGATION_TIMEOUT_MS):
        self.headless, self.timeout_ms = headless, timeout_ms

    def scrape(self, query: str, max_results: int = 50, status_callback: StatusCallback | None = None) -> list[dict]:
        if max_results < 1: raise ValueError("Maximum results must be at least 1.")
        notify = status_callback or (lambda **_: None)
        records: list[dict] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(locale="en-IN", timezone_id="Asia/Kolkata", viewport={"width": 1440, "height": 900})
            page = context.new_page(); page.set_default_timeout(self.timeout_ms)
            try:
                notify(stage="searching", message="Opening Google Maps", progress=8, total_raw=0, preview=[])
                page.goto(f"https://www.google.com/maps/search/{quote_plus(query)}", wait_until="domcontentloaded")
                self._accept_consent(page)
                urls = self._collect_urls(page, max_results, notify)
                for index, url in enumerate(urls, 1):
                    notify(stage="scraping", message=f"Scraping business {index} of {len(urls)}",
                           progress=25 + int(58 * (index - 1) / max(len(urls), 1)),
                           total_raw=len(records), preview=records[-10:])
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                        page.wait_for_selector("h1", timeout=15_000)
                        records.append(self._extract(page, url))
                    except (PlaywrightTimeout, Exception) as exc:
                        LOG.warning("Could not read listing %s: %s", url, exc)
                notify(stage="scraping", message="Business details collected", progress=84,
                       total_raw=len(records), preview=records[-10:])
            finally:
                context.close(); browser.close()
        return records

    def _collect_urls(self, page, max_results: int, notify: StatusCallback) -> list[str]:
        seen: dict[str, None] = {}
        feed = page.locator("div[role='feed']")
        for _ in range(SCROLL_ROUNDS):
            for anchor in page.locator("a[href*='/maps/place/']").all():
                href = anchor.get_attribute("href")
                if href: seen.setdefault(href.split("&")[0], None)
                if len(seen) >= max_results: break
            found = min(len(seen), max_results)
            notify(stage="searching", message=f"Found {found} listings", progress=min(24, 8 + found * 16 // max(max_results, 1)),
                   total_raw=0, preview=[])
            if len(seen) >= max_results: break
            if feed.count(): feed.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            else: page.mouse.wheel(0, 5000)
            page.wait_for_timeout(1200)
        return list(seen)[:max_results]

    def _extract(self, page, url: str) -> dict:
        name = self._text(page, "h1")
        category = self._text(page, "button[jsaction*='category']") or self._text(page, "button.DkEaL")
        rating_text = (self._attr(page, "div.F7nice span[aria-hidden='true']", "textContent") or
                       self._attr(page, "span[role='img'][aria-label*='star']", "aria-label"))
        reviews_text = (self._attr(page, "button[jsaction*='reviewChart']", "aria-label") or
                        self._attr(page, "span[aria-label*='review']", "aria-label"))
        address = self._aria_value(page, "button[data-item-id='address']", "Address:")
        phone = self._phone(page)
        website = self._attr(page, "a[data-item-id='authority']", "href")
        return {"business_name": name, "category": category, "phone": phone,
                "rating": self._number(rating_text), "reviews": int(self._number(reviews_text) or 0),
                "address": address, "website": website, "maps_link": url}

    def _phone(self, page):
        selectors = ("button[data-item-id^='phone:tel:']", "button[aria-label^='Phone:']", "a[href^='tel:']")
        for selector in selectors:
            value = self._attr(page, selector, "aria-label") or self._attr(page, selector, "href")
            value = re.sub(r"^(Phone:|tel:)\s*", "", value, flags=re.I).strip()
            if re.search(r"\d{7,}", re.sub(r"\D", "", value)): return value
        try:
            text = page.locator("body").inner_text(timeout=3000)
            match = re.search(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}", text)
            return match.group(0) if match else ""
        except Exception: return ""

    @staticmethod
    def _text(page, selector):
        locator = page.locator(selector).first
        try: return locator.inner_text().strip() if locator.count() else ""
        except Exception: return ""
    @staticmethod
    def _attr(page, selector, name):
        locator = page.locator(selector).first
        try: return (locator.get_attribute(name) or "").strip() if locator.count() else ""
        except Exception: return ""
    def _aria_value(self, page, selector, prefix):
        value = self._attr(page, selector, "aria-label")
        return re.sub(rf"^{re.escape(prefix)}\s*", "", value, flags=re.I).strip()
    @staticmethod
    def _number(value):
        match = re.search(r"[\d,.]+", str(value or ""))
        return match.group(0).replace(",", "") if match else ""
    @staticmethod
    def _accept_consent(page):
        try:
            button = page.get_by_role("button", name=re.compile("Accept all|I agree", re.I))
            if button.count(): button.first.click(timeout=3000)
        except Exception: pass
