from __future__ import annotations
import asyncio
import re
from typing import AsyncIterator
import httpx
from bs4 import BeautifulSoup
from models import Listing
from scrapers.base import BaseScraper, HEADERS


def _parse_price(text: str) -> tuple[int | None, int | None]:
    """Returns (total_price, price_per_m2). OLX shows only total price."""
    digits = re.sub(r"\s+", "", text or "")
    m = re.search(r"(\d+)", digits)
    if m:
        return int(m.group(1)), None
    return None, None


def _parse_area(text: str) -> float | None:
    m = re.search(r"(\d+[,.]?\d*)\s*m", text or "")
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _parse_rooms(text: str) -> int | None:
    m = re.search(r"(\d+)", text or "")
    return int(m.group(1)) if m else None


class OlxScraper(BaseScraper):
    source = "olx"

    async def scrape(self, url: str) -> AsyncIterator[Listing]:
        async with httpx.AsyncClient() as client:
            html = await self.fetch_html(url, client)

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("[data-cy='l-card']")

        for card in cards:
            link_tag = card.select_one("a[href]")
            if not link_tag:
                continue
            href = link_tag["href"]
            if not href.startswith("http"):
                href = "https://www.olx.pl" + href

            title_tag = card.select_one("h4, h6, [data-testid='ad-title']")
            title = title_tag.get_text(strip=True) if title_tag else "Brak tytułu"

            price_tag = card.select_one("[data-testid='ad-price'], .css-10b0gli")
            price_text = price_tag.get_text(strip=True) if price_tag else ""
            price, _ = _parse_price(price_text)

            params = card.select("[data-testid='advert-details-list'] li, .css-1xv69sj li")
            area, rooms = None, None
            for p in params:
                t = p.get_text(strip=True)
                if "m²" in t or "m2" in t:
                    area = _parse_area(t)
                elif "pokoi" in t.lower() or "pokój" in t.lower() or "pok." in t.lower():
                    rooms = _parse_rooms(t)

            location_tag = card.select_one("[data-testid='location-date'], .css-1osdpkm")
            location = location_tag.get_text(strip=True).split("-")[0].strip() if location_tag else None

            await asyncio.sleep(0)
            yield Listing(
                url=href,
                source=self.source,
                title=title,
                price=price,
                area=area,
                rooms=rooms,
                location=location,
            )
