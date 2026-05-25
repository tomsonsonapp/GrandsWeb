import sqlite3
from pathlib import Path
from models import Listing, EvaluationResult


def init_db(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            url TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT,
            price INTEGER,
            price_per_m2 INTEGER,
            area REAL,
            rooms INTEGER,
            location TEXT,
            score INTEGER,
            is_match INTEGER,
            reasoning TEXT,
            found_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def is_seen(conn: sqlite3.Connection, url: str) -> bool:
    row = conn.execute("SELECT 1 FROM listings WHERE url = ?", (url,)).fetchone()
    return row is not None


def save_listing(conn: sqlite3.Connection, result: EvaluationResult) -> None:
    l = result.listing
    conn.execute(
        """INSERT OR IGNORE INTO listings
           (url, source, title, price, price_per_m2, area, rooms, location,
            score, is_match, reasoning, found_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            l.url, l.source, l.title, l.price, l.price_per_m2,
            l.area, l.rooms, l.location,
            result.score, int(result.is_match), result.reasoning,
            l.found_at.isoformat(),
        ),
    )
    conn.commit()
