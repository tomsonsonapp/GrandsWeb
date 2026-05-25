from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator
import httpx
from models import Listing

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9",
}


class BaseScraper(ABC):
    source: str

    async def fetch_html(self, url: str, client: httpx.AsyncClient) -> str:
        resp = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        resp.raise_for_status()
        return resp.text

    @abstractmethod
    async def scrape(self, url: str) -> AsyncIterator[Listing]: ...

    async def run(self, url: str) -> list[Listing]:
        results = []
        async for listing in self.scrape(url):
            results.append(listing)
        return results
