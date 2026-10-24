"""Translation memory: never pay twice for the same page.

A page is identified by what the translator would actually receive: the
recognised source texts, the language pair, the translator and the extra
context. If all of that is unchanged, the stored translations are reused and
no request is sent (no tokens spent). Qt-free so it can be tested anywhere.
"""

import hashlib
import json
import os
import sqlite3
import threading
import time
from typing import Optional, Sequence


def page_key(texts: Sequence[str], source_lang: str, target_lang: str,
             translator: str, extra_context: str = "") -> str:
    payload = json.dumps(
        {
            "t": [" ".join((t or "").split()) for t in texts],
            "s": source_lang,
            "d": target_lang,
            "m": translator,
            "c": (extra_context or "").strip(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TranslationMemory:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS pages ("
                "key TEXT PRIMARY KEY, translations TEXT NOT NULL, "
                "created REAL NOT NULL, hits INTEGER NOT NULL DEFAULT 0)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def get(self, key: str, expected_count: int) -> Optional[list[str]]:
        """Stored translations for this page, or None (also if the block count differs)."""
        with self._lock, self._connect() as db:
            row = db.execute("SELECT translations FROM pages WHERE key = ?", (key,)).fetchone()
            if not row:
                return None
            try:
                values = json.loads(row[0])
            except (TypeError, ValueError):
                return None
            if not isinstance(values, list) or len(values) != expected_count:
                return None
            db.execute("UPDATE pages SET hits = hits + 1 WHERE key = ?", (key,))
            return [str(v) for v in values]

    def put(self, key: str, translations: Sequence[str]) -> None:
        values = [t or "" for t in translations]
        if not values or not any(v.strip() for v in values):
            return  # never remember an empty or failed result
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO pages(key, translations, created, hits) "
                "VALUES (?, ?, ?, COALESCE((SELECT hits FROM pages WHERE key = ?), 0))",
                (key, json.dumps(values, ensure_ascii=False), time.time(), key),
            )

    def stats(self) -> dict:
        with self._lock, self._connect() as db:
            pages, hits = db.execute("SELECT COUNT(*), COALESCE(SUM(hits), 0) FROM pages").fetchone()
        return {"pages": int(pages), "reused": int(hits)}

    def clear(self) -> None:
        with self._lock, self._connect() as db:
            db.execute("DELETE FROM pages")
