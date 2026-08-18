"""Der Kern: fuer jede gespeicherte Suche alle Quellen abfragen, normalisieren,
lokal gegenfiltern, in den Speicher schreiben und bei relevanten Events melden.
"""
from schema import Vehicle


def matches(v: Vehicle, f: dict) -> bool:
    """Lokaler Gegencheck. Die Quelle filtert grob per API-Parameter; hier wird
    exakt geprueft, weil nicht jede Quelle jeden Parameter serverseitig kann."""
    if f.get("make"):
        needle = f["make"].lower()
        if needle not in v.make.lower() and needle not in v.model.lower():
            return False
    if f.get("model"):
        needle = f["model"].lower()
        if needle not in v.model.lower() and needle not in v.variant.lower():
            return False
    if f.get("price_max") is not None and (v.price is None or v.price > f["price_max"]):
        return False
    if f.get("price_min") is not None and (v.price is None or v.price < f["price_min"]):
        return False
    if f.get("year_min") is not None and (v.year is None or v.year < f["year_min"]):
        return False
    if f.get("mileage_max") is not None and (v.mileage_km is None or v.mileage_km > f["mileage_max"]):
        return False
    if f.get("seller_type") and v.seller_type and v.seller_type != f["seller_type"]:
        return False
    return True


class Engine:
    def __init__(self, providers, store, searches, notifier):
        self.providers = providers
        self.store = store
        self.searches = searches
        self.notifier = notifier

    def _provider_for(self, source: str):
        for p in self.providers:
            if p.supports(source):
                return p
        return None

    def run_once(self):
        for s in self.searches:
            flt = s.get("query", {})
            for source in s.get("sources", []):
                prov = self._provider_for(source)
                if prov is None:
                    continue  # keine Quelle konfiguriert -> still ueberspringen
                q = dict(flt)
                q["source"] = source
                try:
                    for raw in prov.search(q):
                        v = prov.normalize(raw, source)
                        if not matches(v, flt):
                            continue
                        ev = self.store.upsert(v)
                        if ev and ev.get("type") in ("new", "price_changed"):
                            self.notifier(s.get("name", "?"), ev, v)
                except Exception as e:
                    print(f"[warn] {prov.name}/{source}: {e}", flush=True)
