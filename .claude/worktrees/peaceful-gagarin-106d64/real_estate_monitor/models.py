from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Listing:
    url: str
    source: str  # "olx" | "otodom" | "nieruchomosci"
    title: str
    price: Optional[int] = None          # PLN
    price_per_m2: Optional[int] = None   # PLN/m²
    area: Optional[float] = None         # m²
    rooms: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    found_at: datetime = field(default_factory=datetime.now)

    def to_eval_text(self) -> str:
        parts = [f"Tytuł: {self.title}"]
        if self.price:
            parts.append(f"Cena: {self.price:,} PLN".replace(",", " "))
        if self.price_per_m2:
            parts.append(f"Cena/m²: {self.price_per_m2:,} PLN/m²".replace(",", " "))
        if self.area:
            parts.append(f"Metraż: {self.area} m²")
        if self.rooms:
            parts.append(f"Liczba pokoi: {self.rooms}")
        if self.location:
            parts.append(f"Lokalizacja: {self.location}")
        if self.description:
            parts.append(f"Opis: {self.description[:800]}")
        parts.append(f"Link: {self.url}")
        return "\n".join(parts)


@dataclass
class EvaluationResult:
    listing: Listing
    is_match: bool
    score: int          # 0-100
    reasoning: str
