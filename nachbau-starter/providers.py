"""Quellen-Adapter (Provider).

Jeder Provider kapselt EINE Datenquelle hinter derselben Schnittstelle:
  - supports(source): bediene ich diese Quelle?
  - search(query):    liefere Rohdaten (Generator, seitenweise)
  - normalize(raw):   forme Rohdaten in ein Vehicle

Neue Quelle anbinden = neue Provider-Klasse. Der Rest bleibt unveraendert.
"""
import requests
from schema import Vehicle


class Provider:
    name = "base"

    def supports(self, source: str) -> bool:
        raise NotImplementedError

    def search(self, query: dict):
        raise NotImplementedError

    def normalize(self, raw: dict, source: str) -> Vehicle:
        raise NotImplementedError


class CarapisProvider(Provider):
    """Aggregator: liefert Kleinanzeigen, mobile.de, AutoScout24 u.v.m.

    Ein Anbieter fuer die schwer zugaenglichen Quellen. Doku:
    https://carapis.com/api/getting-started
    """
    name = "carapis"
    BASE = "https://api.carapis.com/v2"

    # unsere generischen Namen -> Carapis-Slugs
    SLUGS = {
        "kleinanzeigen": "kleinanzeigen",
        "mobile": "mobile-de",
        "autoscout": "autoscout24",
    }

    def __init__(self, api_key: str, timeout: int = 30):
        self.key = api_key
        self.timeout = timeout

    def supports(self, source: str) -> bool:
        return source in self.SLUGS

    def search(self, query: dict):
        slug = self.SLUGS[query["source"]]
        page = 1
        limit = query.get("limit", 50)
        while True:
            params = {"source": slug, "limit": limit, "page": page}
            for k in ("make", "model", "price_max", "price_min", "year_min", "mileage_max"):
                if query.get(k) is not None:
                    params[k] = query[k]
            r = requests.get(
                f"{self.BASE}/listings",
                params=params,
                headers={"Authorization": f"Bearer {self.key}"},
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            for raw in results:
                yield raw
            if not results or page * limit >= data.get("count", 0):
                break
            page += 1

    def normalize(self, raw: dict, source: str) -> Vehicle:
        return Vehicle(
            source=source,
            source_id=str(raw.get("id", "")).split("_")[-1],
            url=raw.get("url", ""),
            make=raw.get("make", ""),
            model=raw.get("model", ""),
            variant=raw.get("trim", "") or raw.get("variant", ""),
            year=raw.get("year"),
            mileage_km=raw.get("mileage") or raw.get("mileage_km"),
            power_kw=raw.get("power_kw"),
            price=raw.get("price"),
            currency=raw.get("currency", "EUR"),
            fuel=raw.get("fuel", ""),
            gearbox=raw.get("gearbox", ""),
            zip_code=str(raw.get("zip", "") or raw.get("zip_code", "")),
            city=raw.get("city", ""),
            seller_type=raw.get("seller_type", ""),
            vin=raw.get("vin", ""),
            images=raw.get("photos", []) or [],
            raw=raw,
        )


class EbayBrowseProvider(Provider):
    """Offizielle eBay Browse API (frei, dokumentiert).

    Kostenloser, sauberer Einstieg. OAuth-App-Token noetig:
    https://developer.ebay.com/api-docs/buy/browse/overview.html
    Hinweis: Die Motors-Kategorie-ID unterscheidet sich je Marktplatz --
    fuer EBAY_DE die passende category_ids in der config setzen.
    """
    name = "ebay"
    BASE = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    def __init__(self, oauth_token: str, marketplace: str = "EBAY_DE", timeout: int = 30):
        self.token = oauth_token
        self.marketplace = marketplace
        self.timeout = timeout

    def supports(self, source: str) -> bool:
        return source == "ebay"

    def search(self, query: dict):
        offset = 0
        limit = query.get("limit", 50)
        q = query.get("q") or f"{query.get('make', '')} {query.get('model', '')}".strip()
        while True:
            params = {"q": q, "limit": limit, "offset": offset}
            if query.get("category_ids"):
                params["category_ids"] = query["category_ids"]
            if query.get("price_max"):
                params["filter"] = f"price:[..{query['price_max']}],priceCurrency:EUR"
            r = requests.get(
                self.BASE,
                params=params,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
            items = data.get("itemSummaries", [])
            for it in items:
                yield it
            offset += limit
            if offset >= data.get("total", 0) or not items:
                break

    def normalize(self, raw: dict, source: str) -> Vehicle:
        price = raw.get("price", {}) or {}
        value = price.get("value")
        img = raw.get("image", {}) or {}
        return Vehicle(
            source="ebay",
            source_id=str(raw.get("itemId", "")),
            url=raw.get("itemWebUrl", ""),
            model=raw.get("title", ""),
            price=int(float(value)) if value else None,
            currency=price.get("currency", "EUR"),
            seller_type="dealer" if (raw.get("seller", {}) or {}).get("username") else "",
            images=[img["imageUrl"]] if img.get("imageUrl") else [],
            raw=raw,
        )
