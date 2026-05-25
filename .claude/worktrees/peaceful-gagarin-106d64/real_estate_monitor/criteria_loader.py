"""
Jednorazowe narzędzie do wygenerowania criteria_prompt.txt z NotebookLM.

Uruchom raz po dodaniu 100 dokumentów do NotebookLM:
    python criteria_loader.py

Skrypt połączy się z NotebookLM przez MCP (tylko przy uruchamianiu przez Claude Code),
wydobędzie kryteria zakupu i zapisze do criteria_prompt.txt.

Alternatywnie: edytuj criteria_prompt.txt ręcznie.
"""

import sys
from pathlib import Path

NOTEBOOK_ID = "d80e0301-4aa0-4a5d-a16b-fbea512ca34d"
OUTPUT_FILE = "criteria_prompt.txt"

MANUAL_TEMPLATE = """Jesteś ekspertem od nieruchomości oceniającym oferty zakupu mieszkań w Polsce.

KRYTERIA ZAKUPU (wypełnij na podstawie swoich dokumentów):
- Lokalizacja: [np. Warszawa — Mokotów, Ursynów, Wilanów]
- Maksymalna cena: [np. 800 000 PLN]
- Maksymalna cena/m²: [np. 12 000 PLN/m²]
- Minimalna powierzchnia: [np. 50 m²]
- Liczba pokoi: [np. min. 3 pokoje]
- Stan techniczny: [np. dobry stan lub do lekkiego remontu]
- Rok budowy: [np. po 2000 roku]
- Dodatkowe wymagania: [np. balkon, miejsce parkingowe]

ZASADY OCENY:
- score 80-100: Idealnie spełnia wszystkie kryteria
- score 60-79: Spełnia większość kryteriów, warte rozważenia
- score 40-59: Częściowe dopasowanie, możliwe do negocjacji
- score 0-39: Nie spełnia kluczowych kryteriów

Zwróć WYŁĄCZNIE JSON:
{"score": <0-100>, "is_match": <true/false>, "reasoning": "<uzasadnienie>"}
"""


def generate_from_template():
    Path(OUTPUT_FILE).write_text(MANUAL_TEMPLATE, encoding="utf-8")
    print(f"Szablon kryteriów zapisany do {OUTPUT_FILE}")
    print("Edytuj plik i uzupełnij swoje kryteria zakupu!")


if __name__ == "__main__":
    if not Path(OUTPUT_FILE).exists():
        generate_from_template()
    else:
        print(f"{OUTPUT_FILE} już istnieje. Usuń go jeśli chcesz wygenerować od nowa.")
