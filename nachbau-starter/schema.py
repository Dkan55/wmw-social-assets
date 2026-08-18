"""Einheitliches Fahrzeug-Datenmodell.

Jede Quelle (Aggregator, eBay-API, ...) liefert unterschiedliche Rohdaten.
Alles wird auf diese eine Struktur normalisiert, damit der Rest des Systems
(Dedup, Filter, Events) quellenunabhaengig arbeitet.
"""
from dataclasses import dataclass, field
from typing import Optional
import re
import hashlib


@dataclass
class Vehicle:
    source: str                 # "kleinanzeigen" | "mobile" | "autoscout" | "ebay"
    source_id: str              # ID des Inserats bei der Quelle
    url: str
    make: str = ""
    model: str = ""
    variant: str = ""
    year: Optional[int] = None          # Erstzulassung (Jahr)
    mileage_km: Optional[int] = None
    power_kw: Optional[int] = None
    price: Optional[int] = None
    currency: str = "EUR"
    fuel: str = ""
    gearbox: str = ""
    zip_code: str = ""
    city: str = ""
    seller_type: str = ""       # "private" | "dealer" | ""
    vin: str = ""
    images: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def identity(self) -> str:
        """Eindeutig pro Inserat und Quelle."""
        return f"{self.source}:{self.source_id}"

    def fingerprint(self) -> str:
        """Quellenuebergreifender Fingerabdruck fuer Dublettenerkennung.

        Dasselbe Auto steht oft auf mehreren Boersen gleichzeitig. Wo eine
        Fahrgestellnummer (VIN) vorliegt, ist der Fall eindeutig. Sonst bilden
        wir einen Fingerabdruck aus Marke/Modell, Jahr, Laufleistungs-Klasse,
        Leistung und Preis-Klasse (grob gerundet, damit kleine Abweichungen
        zwischen Boersen nicht als zwei Autos durchgehen).
        """
        if self.vin:
            return "vin:" + self.vin.upper()
        mk = re.sub(r"\s+", "", (self.make + self.model).lower())
        km = "" if self.mileage_km is None else str(round(self.mileage_km / 5000))
        pr = "" if self.price is None else str(round(self.price / 500))
        base = "|".join([mk, str(self.year or ""), km, str(self.power_kw or ""), pr])
        return "fp:" + hashlib.sha1(base.encode()).hexdigest()[:16]
