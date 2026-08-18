"""Zustandsspeicher + Ereigniserkennung (SQLite).

Beim ersten Sehen eines Inserats -> Event "new" (ausser es ist eine Dublette
eines bereits aktiven Inserats aus einer anderen Quelle -> "duplicate").
Bei geaendertem Preis -> Event "price_changed". Sonst -> None (nur last_seen
aktualisiert). Genau diese Umkehr macht aus einer Suche einen Suchagenten.
"""
import sqlite3
import json
import time
from schema import Vehicle


class Store:
    def __init__(self, path: str = "listings.db"):
        self.db = sqlite3.connect(path)
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS listings(
                identity    TEXT PRIMARY KEY,
                fingerprint TEXT,
                source      TEXT,
                url         TEXT,
                price       INTEGER,
                data        TEXT,
                first_seen  REAL,
                last_seen   REAL,
                active      INTEGER DEFAULT 1
            )"""
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_fp ON listings(fingerprint)")
        self.db.commit()

    def upsert(self, v: Vehicle):
        now = time.time()
        row = self.db.execute(
            "SELECT price FROM listings WHERE identity=?", (v.identity(),)
        ).fetchone()

        if row is None:
            dup = self.db.execute(
                "SELECT identity FROM listings WHERE fingerprint=? AND active=1 LIMIT 1",
                (v.fingerprint(),),
            ).fetchone()
            event = {"type": "duplicate"} if dup else {"type": "new"}
            self.db.execute(
                "INSERT INTO listings VALUES(?,?,?,?,?,?,?,?,1)",
                (v.identity(), v.fingerprint(), v.source, v.url, v.price,
                 json.dumps(v.raw), now, now),
            )
        else:
            old_price = row[0]
            self.db.execute(
                "UPDATE listings SET last_seen=?, price=?, active=1 WHERE identity=?",
                (now, v.price, v.identity()),
            )
            if v.price is not None and old_price is not None and v.price != old_price:
                event = {"type": "price_changed", "old": old_price, "new": v.price}
            else:
                event = None

        self.db.commit()
        return event

    def mark_stale(self, older_than_seconds: int = 86400):
        """Inserate, die laenger nicht mehr gesehen wurden, als inaktiv markieren
        (Grundlage fuer ein spaeteres 'verschwunden'-Event)."""
        cutoff = time.time() - older_than_seconds
        self.db.execute("UPDATE listings SET active=0 WHERE last_seen < ?", (cutoff,))
        self.db.commit()
