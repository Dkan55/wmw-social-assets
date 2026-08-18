"""Einstiegspunkt: Konfiguration laden, Provider bauen, Poll-Schleife starten.

    python run.py config.yaml
"""
import sys
import time
import yaml
import requests

from store import Store
from providers import CarapisProvider, EbayBrowseProvider
from engine import Engine


def build_notifier(cfg):
    webhook = (cfg.get("notify") or {}).get("webhook_url")

    def notify(search_name, ev, v):
        line = (f"[{search_name}] {ev['type'].upper()} - "
                f"{v.make} {v.model} {v.year or ''} | "
                f"{v.price} {v.currency} | {v.source} | {v.url}")
        if ev["type"] == "price_changed":
            line += f"  ({ev['old']} -> {ev['new']})"
        print(line, flush=True)
        if webhook:
            try:
                requests.post(webhook, timeout=10, json={
                    "search": search_name,
                    "event": ev,
                    "vehicle": {
                        "make": v.make, "model": v.model, "year": v.year,
                        "price": v.price, "currency": v.currency,
                        "url": v.url, "source": v.source,
                    },
                })
            except Exception as e:
                print(f"[warn] webhook: {e}", flush=True)

    return notify


def build_providers(cfg):
    providers = []
    pc = cfg.get("providers", {})
    if pc.get("carapis", {}).get("api_key"):
        providers.append(CarapisProvider(pc["carapis"]["api_key"]))
    if pc.get("ebay", {}).get("oauth_token"):
        providers.append(EbayBrowseProvider(
            pc["ebay"]["oauth_token"],
            pc["ebay"].get("marketplace", "EBAY_DE"),
        ))
    return providers


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    cfg = yaml.safe_load(open(path, encoding="utf-8"))

    providers = build_providers(cfg)
    if not providers:
        print("Kein Provider konfiguriert. Trage einen API-Key in config.yaml ein.")
        return

    store = Store(cfg.get("database", "listings.db"))
    searches = cfg.get("searches", [])
    engine = Engine(providers, store, searches, build_notifier(cfg))
    interval = cfg.get("poll_interval_seconds", 120)

    names = ", ".join(p.name for p in providers)
    print(f"Start. Provider: {names} | Suchen: {len(searches)} | Intervall: {interval}s")
    while True:
        t0 = time.time()
        engine.run_once()
        store.mark_stale()
        dt = time.time() - t0
        time.sleep(max(1, interval - dt))


if __name__ == "__main__":
    main()
