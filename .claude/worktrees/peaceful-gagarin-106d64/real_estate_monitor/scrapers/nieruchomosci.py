from __future__ import annotations
import asyncio
import re
from typing import AsyncIterator
import httpx
from bs4 import BeautifulSoup
from models import Listing
from scrapers.base import BaseScraper, HEADERS


def _parse_price(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def _parse_area(text: str) -> float | None:
    m = re.search(r"(\d+[,.]?\d*)", text or "")
    return float(m.group(1).replace(",", ".")) if m else None


class NieruchomosciScraper(BaseScraper):
    source = "nieruchomosci"

    async def scrape(self, url: str) -> AsyncIterator[Listing]:
        async with httpx.AsyncClient() as client:
            html = await self.fetch_html(url, client)

        soup = BeautifulSoup(html, "lxml")

        # nieruchomosci-online.pl structure
        cards = soup.select(".listing-item, .offer-item, article.property")
        if not cards:
            # fallback: generic offer cards
            cards = soup.select("[class*='offer'], [class*='listing']")

        for card in cards:
            link_tag = card.select_one("a[href]")
            if not link_tag:
                continue
            href = link_tag["href"]
            if not href.startswith("http"):
                href = "https://www.nieruchomosci-online.pl" + href

            title_tag = card.select_one("h2, h3, .title, [class*='title']")
            title = title_tag.get_text(strip=True) if title_tag else "Brak tytułu"

            price_tag = card.select_one(".price, [class*='price']")
            price = _parse_price(price_tag.get_text() if price_tag else "")

            area_tag = card.select_one("[class*='area'], [class*='surface']")
            area = _parse_area(area_tag.get_text() if area_tag else "")

            location_tag = card.select_one(".location, [class*='location'], [class*='address']")
            location = location_tag.get_text(strip=True) if location_tag else None

            await asyncio.sleep(0)
            yield Listing(
                url=href,
                source=self.source,
                title=title,
                price=price,
                area=area,
                location=location,
            )
