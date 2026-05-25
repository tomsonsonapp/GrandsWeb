from __future__ import annotations
import json
import os
import anthropic
from models import Listing, EvaluationResult

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def load_criteria(criteria_file: str) -> str:
    try:
        with open(criteria_file, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return _default_criteria()


def _default_criteria() -> str:
    return (
        "Jesteś ekspertem od nieruchomości oceniającym oferty zakupu mieszkań w Polsce. "
        "Oceń każdą ofertę pod kątem atrakcyjności inwestycyjnej. "
        "Bierz pod uwagę: cenę za m², lokalizację, metraż i liczbę pokoi. "
        "Faworyzuj oferty poniżej średniej rynkowej dla danej lokalizacji. "
        "Zwróć JSON: {\"score\": 0-100, \"is_match\": true/false, \"reasoning\": \"...\"}. "
        "is_match = true jeśli score >= 60."
    )


def evaluate(listing: Listing, criteria: str, model: str, threshold: int) -> EvaluationResult:
    client = _get_client()

    system = (
        f"{criteria}\n\n"
        "Odpowiedz WYŁĄCZNIE poprawnym JSON w formacie:\n"
        '{"score": <liczba 0-100>, "is_match": <true/false>, "reasoning": "<uzasadnienie po polsku>"}'
    )

    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system,
        messages=[
            {
                "role": "user",
                "content": f"Oceń poniższe ogłoszenie:\n\n{listing.to_eval_text()}",
            }
        ],
    )

    text = response.content[0].text.strip()
    # Extract JSON even if model added surrounding text
    start = text.find("{")
    end = text.rfind("}") + 1
    data = json.loads(text[start:end])

    score = int(data.get("score", 0))
    is_match = bool(data.get("is_match", score >= threshold))
    reasoning = data.get("reasoning", "")

    return EvaluationResult(
        listing=listing,
        is_match=is_match,
        score=score,
        reasoning=reasoning,
    )
