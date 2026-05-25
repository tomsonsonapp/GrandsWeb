from __future__ import annotations
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from database import init_db, is_seen, save_listing
from evaluator import evaluate, load_criteria
from models import Listing
from notifier import send_email
from scrapers.nieruchomosci import NieruchomosciScraper
from scrapers.olx import OlxScraper
from scrapers.otodom import OtodomScraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

SCRAPERS = {
    "olx": OlxScraper(),
    "otodom": OtodomScraper(),
    "nieruchomosci": NieruchomosciScraper(),
}


def load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


async def run_scraper_job(name: str, url: str, cfg: dict, criteria: str, conn) -> None:
    scraper = SCRAPERS.get(name)
    if not scraper:
        return

    ai_cfg = cfg.get("ai", {})
    model = ai_cfg.get("model", "claude-sonnet-4-6")
    threshold = ai_cfg.get("match_threshold", 60)

    log.info(f"[{name.upper()}] Scrapuję: {url}")
    try:
        listings = await scraper.run(url)
    except Exception as e:
        log.error(f"[{name.upper()}] Błąd scrapowania: {e}")
        return

    new_count = 0
    match_count = 0

    for listing in listings:
        if not listing.url or is_seen(conn, listing.url):
            continue

        new_count += 1
        log.info(f"  Nowe ogłoszenie: {listing.title[:60]}")

        try:
            result = evaluate(listing, criteria, model, threshold)
            save_listing(conn, result)

            if result.is_match:
                match_count += 1
                log.info(f"  ✅ MATCH ({result.score}/100) — wysyłam email")
                try:
                    send_email(result, cfg)
                except Exception as e:
                    log.error(f"  Błąd wysyłki email: {e}")
            else:
                log.info(f"  ❌ score={result.score}/100 — pomijam")
        except Exception as e:
            log.error(f"  Błąd oceny AI: {e}")

    log.info(f"[{name.upper()}] Znaleziono {len(listings)} ogłoszeń, {new_count} nowych, {match_count} pasujących")


async def run_all(cfg: dict, criteria: str, conn) -> None:
    tasks = []
    for name, scraper_cfg in cfg.get("scrapers", {}).items():
        if not scraper_cfg.get("enabled", False):
            continue
        url = scraper_cfg["url"]
        tasks.append(run_scraper_job(name, url, cfg, criteria, conn))
    await asyncio.gather(*tasks)


# ── CLI ──────────────────────────────────────────────────────────────────────

async def cmd_run(args, cfg, criteria, conn):
    await run_all(cfg, criteria, conn)


async def cmd_test_scrapers(args, cfg, criteria, conn):
    for name, scraper_cfg in cfg.get("scrapers", {}).items():
        if not scraper_cfg.get("enabled", False):
            continue
        scraper = SCRAPERS.get(name)
        url = scraper_cfg["url"]
        log.info(f"=== TEST: {name.upper()} ===")
        try:
            listings = await scraper.run(url)
            for l in listings[:3]:
                print(f"  [{l.source}] {l.title[:60]}")
                print(f"    Cena: {l.price} | Metraż: {l.area} | Lokalizacja: {l.location}")
                print(f"    URL: {l.url[:80]}")
        except Exception as e:
            log.error(f"  Błąd: {e}")


async def cmd_test_email(args, cfg, criteria, conn):
    from models import EvaluationResult
    from datetime import datetime
    dummy = Listing(
        url="https://example.com/test",
        source="test",
        title="Testowe mieszkanie 3-pokojowe, Mokotów",
        price=650000,
        price_per_m2=8200,
        area=79.0,
        rooms=3,
        location="Warszawa, Mokotów",
    )
    result = EvaluationResult(
        listing=dummy,
        is_match=True,
        score=82,
        reasoning="To jest testowa wiadomość z systemu monitorowania nieruchomości.",
    )
    send_email(result, cfg)
    log.info("Email testowy wysłany!")


async def cmd_eval(args, cfg, criteria, conn):
    from models import EvaluationResult
    ai_cfg = cfg.get("ai", {})
    model = ai_cfg.get("model", "claude-sonnet-4-6")
    threshold = ai_cfg.get("match_threshold", 60)
    dummy = Listing(
        url="https://example.com",
        source="manual",
        title=args.text,
        description=args.text,
    )
    result = evaluate(dummy, criteria, model, threshold)
    print(f"\nScore: {result.score}/100")
    print(f"Match: {'✅ TAK' if result.is_match else '❌ NIE'}")
    print(f"Uzasadnienie: {result.reasoning}")


def main():
    parser = argparse.ArgumentParser(description="Monitor ogłoszeń nieruchomości")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("run", help="Jednorazowe uruchomienie scraperów")
    sub.add_parser("test-scrapers", help="Test scraperów (drukuje 3 oferty z każdego)")
    sub.add_parser("test-email", help="Wysyłka testowego emaila")
    eval_p = sub.add_parser("eval", help="Oceń tekst ogłoszenia przez AI")
    eval_p.add_argument("text", help="Tekst ogłoszenia do oceny")
    sub.add_parser("daemon", help="Uruchom scheduler (domyślne)")

    args = parser.parse_args()

    cfg = load_config()
    criteria = load_criteria(cfg.get("criteria_file", "criteria_prompt.txt"))
    conn = init_db(cfg["database"]["path"])

    async def dispatch():
        if args.cmd == "run":
            await cmd_run(args, cfg, criteria, conn)
        elif args.cmd == "test-scrapers":
            await cmd_test_scrapers(args, cfg, criteria, conn)
        elif args.cmd == "test-email":
            await cmd_test_email(args, cfg, criteria, conn)
        elif args.cmd == "eval":
            await cmd_eval(args, cfg, criteria, conn)
        else:
            # daemon mode (default)
            interval = min(
                s.get("interval_minutes", 30)
                for s in cfg.get("scrapers", {}).values()
                if s.get("enabled")
            )
            log.info(f"Uruchamiam scheduler co {interval} minut...")
            scheduler = AsyncIOScheduler()
            scheduler.add_job(
                run_all,
                "interval",
                minutes=interval,
                args=[cfg, criteria, conn],
            )
            scheduler.start()
            log.info("Scheduler uruchomiony. Ctrl+C aby zatrzymać.")
            # pierwsze uruchomienie od razu
            await run_all(cfg, criteria, conn)
            try:
                await asyncio.Event().wait()
            except (KeyboardInterrupt, SystemExit):
                scheduler.shutdown()
                log.info("Zatrzymano.")

    asyncio.run(dispatch())


if __name__ == "__main__":
    main()
