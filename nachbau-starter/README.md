# AutoPointer-Nachbau — Daten-Starter

Ein kleiner, lauffähiger Kern des Suchagenten: er fragt Fahrzeug-Quellen ab,
vereinheitlicht die Daten, erkennt Dubletten und meldet **neue** und
**preisgeänderte** Inserate. Genau das Prinzip, mit dem AutoPointer arbeitet —
nur schlank und nachvollziehbar.

## Woher kommen die Daten?

| Quelle | Wie | Warum |
|---|---|---|
| **Kleinanzeigen, mobile.de, AutoScout24** | über den Aggregator **[Carapis](https://carapis.com/)** (eine REST-API, alles normalisiert) | Kleinanzeigen hat keine offizielle Schnittstelle. Ein Aggregator trägt die Beschaffung — du konsumierst nur. |
| **eBay** | offizielle **[eBay Browse API](https://developer.ebay.com/api-docs/buy/browse/overview.html)** (frei) | Sauberer, kostenloser Einstieg zum Beweisen der Technik. |

Weitere Aggregatoren zum Vergleich: **Apify** (fertige Kleinanzeigen-Scraper,
~1,50 $ / 1.000 Treffer), **Marketcheck** (v. a. USA/UK).

> **Rechtlicher Hinweis.** Ein Aggregator verlagert den operativen Aufwand und
> einen Teil des Risikos, nimmt dir die Prüfung aber nicht ab. Lass dir die
> Quellenrechte vertraglich zusichern und hol vor dem Live-Gang eine kurze
> anwaltliche Einschätzung (Datenbankherstellerrecht §§ 87a ff. UrhG, DSGVO bei
> Verkäufer-Kontaktdaten) ein.

## Aufbau

```
run.py         Poll-Schleife + Benachrichtigung
engine.py      pro Suche alle Quellen abfragen, filtern, Events auslösen
providers.py   Adapter je Quelle (Carapis, eBay) — neue Quelle = neue Klasse
schema.py      einheitliches Vehicle-Modell + Dubletten-Fingerabdruck
store.py       SQLite: Zustand + Erkennung von "neu" / "Preis geändert"
```

Datenfluss: `Quelle → normalize → Filter → Dedup/Diff (store) → Event → notify`.

## Loslegen

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml     # Keys und Suchen eintragen
python run.py config.yaml
```

Ohne Key läuft nichts los — trage mindestens einen Provider in `config.yaml`
ein. Für einen ersten Test reicht der eBay-App-Token (frei).

## Eine Suche anlegen

In `config.yaml` unter `searches`:

```yaml
- name: "BMW 3er unter 15k, privat"
  sources: ["kleinanzeigen", "mobile", "ebay"]
  query:
    make: "BMW"
    model: "3er"
    price_max: 15000
    year_min: 2015
    mileage_max: 150000
    seller_type: "private"
```

Jeder Treffer erscheint in der Konsole; mit `notify.webhook_url` wird zusätzlich
ein JSON-POST an dein Backend geschickt (Anbindung an App-Push, CRM o. ä.).

## Nächste Schritte (aus der Referenzarchitektur)

1. **Filter-Matching umdrehen** — bei vielen Nutzern nicht jede Suche einzeln
   abfragen, sondern Filter als Percolate-Queries vorhalten (OpenSearch).
2. **Bild-Fingerabdruck** zur Dubletten-Erkennung ergänzen (perceptual hash).
3. **"verschwunden"-Event** aus `store.mark_stale()` an die Oberfläche bringen.
4. **Zustellung**: WebSocket (Web/Desktop) + APNs/FCM (Mobil).
