from __future__ import annotations
import asyncio
import json
import re
from typing import AsyncIterator
from playwright.async_api import async_playwright, Page
from models import Listing
from scrapers.base import BaseScraper


def _safe_int(val) -> int | None:
    try:
        return int(str(val).replace(" ", "").replace("\xa0", "").split(".")[0])
    except (TypeError, ValueError):
        return None


def _safe_float(val) -> float | None:
    try:
        return float(str(val).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return None


class OtodomScraper(BaseScraper):
    source = "otodom"

    async def scrape(self, url: str) -> AsyncIterator[Listing]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="pl-PL",
            )
            page = await context.new_page()

            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Accept cookies if banner present
            try:
                await page.click("[id='onetrust-accept-btn-handler']", timeout=3000)
                await asyncio.sleep(1)
            except Exception:
                pass

            listings = await self._extract_listings(page)
            await browser.close()

        for l in listings:
            yield l

    async def _extract_listings(self, page: Page) -> list[Listing]:
        # Try JSON-LD / __NEXT_DATA__ first (most reliable)
        results = await self._parse_next_data(page)
        if results:
            return results
        return await self._parse_dom(page)

    async def _parse_next_data(self, page: Page) -> list[Listing]:
        try:
            data_text = await page.eval_on_selector(
                "#__NEXT_DATA__", "el => el.textContent"
            )
            data = json.loads(data_text)
            items = (
                data.get("props", {})
                .get("pageProps", {})
                .get("data", {})
                .get("searchAds", {})
                .get("items", [])
            )
            results = []
            for item in items:
                url = "https://www.otodom.pl/pl/oferta/" + item.get("slug", "")
                price = _safe_int(item.get("totalPrice", {}).get("value"))
                area = _safe_float(item.get("areaInSquareMeters"))
                price_m2 = _safe_int(item.get("pricePerSquareMeter", {}).get("value"))
                rooms_raw = item.get("roomsNumber", "")
                rooms_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX_OR_MORE": 6}
                rooms = rooms_map.get(rooms_raw)
                location_parts = [
                    item.get("locationLabel", {}).get("value", ""),
                ]
                location = ", ".join(p for p in location_parts if p) or None
                title = item.get("title", "Brak tytułu")
                results.append(Listing(
                    url=url,
                    source="otodom",
                    title=title,
                    price=price,
                    price_per_m2=price_m2,
                    area=area,
                    rooms=rooms,
                    location=location,
                ))
            return results
        except Exception:
            return []

    async def _parse_dom(self, page: Page) -> list[Listing]:
        cards = await page.query_selector_all("article[data-cy='listing-item']")
        results = []
        for card in cards:
            try:
                link = await card.query_selector("a[href]")
                href = await link.get_attribute("href") if link else None
                if href and not href.startswith("http"):
                    href = "https://www.otodom.pl" + href

                title_el = await card.query_selector("h3, [data-cy='listing-item-title']")
                title = await title_el.inner_text() if title_el else "Brak tytułu"

                price_el = await card.query_selector("[aria-label='Cena'], strong")
                price_text = await price_el.inner_text() if price_el else ""
                price = _safe_int(re.sub(r"[^\d]", "", price_text))

                results.append(Listing(
                    url=href or "",
                    source="otodom",
                    title=title.strip(),
                    price=price,
                ))
            except Exception:
                continue
        return results
