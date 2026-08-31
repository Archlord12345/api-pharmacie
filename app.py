from __future__ import annotations

import html
import re
import unicodedata
from html.parser import HTMLParser
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query

SOURCE_URL = "https://www.annuaire-medical.cm/fr/pharmacies-de-garde/"

app = FastAPI(
    title="API Pharmacies de garde Cameroun",
    description="Expose les pharmacies de garde depuis annuaire-medical.cm avec filtrage local.",
    version="1.0.0",
)


PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")

AVAILABLE_REGIONS = [
    "Adamaoua",
    "Centre",
    "Est",
    "Extrême-Nord",
    "Littoral",
    "Nord",
    "Nord-Ouest",
    "Ouest",
    "Sud",
    "Sud-Ouest",
]

AVAILABLE_CITIES = [
    "Bafoussam",
    "Bamenda",
    "Bertoua",
    "Buea",
    "Douala",
    "Ebolowa",
    "Garoua",
    "Kribi",
    "Limbe",
    "Maroua",
    "Ngaoundéré",
    "Yaoundé",
]


def normalize(value: str) -> str:
    stripped = unicodedata.normalize("NFD", value)
    no_accents = "".join(char for char in stripped if unicodedata.category(char) != "Mn")
    return no_accents.lower().strip()


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def build_normalized_map(values: list[str]) -> dict[str, str]:
    return {normalize(value): value for value in values}


REGION_MAP = build_normalized_map(AVAILABLE_REGIONS)
CITY_MAP = build_normalized_map(AVAILABLE_CITIES)


def validate_filter_value(value: str | None, mapping: dict[str, str], label: str) -> str | None:
    if not value:
        return value

    match = mapping.get(normalize(value))
    if match:
        return match

    raise HTTPException(
        status_code=400,
        detail=f"{label} inconnue: '{value}'. Valeurs disponibles: {', '.join(mapping.values())}",
    )


class GuardPharmacyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] = []
        self._cell_stack: list[str] = []
        self._active_tags: list[str] = []
        self.items: list[str] = []
        self._item_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._active_tags.append(tag)
        if tag == "tr":
            self._current_row = []
        if tag in {"td", "th"}:
            self._cell_stack.append("")
        if tag == "li":
            self._item_stack.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell_stack:
            text = compact(self._cell_stack.pop())
            if text:
                self._current_row.append(text)
        if tag == "tr" and self._current_row:
            self.rows.append(self._current_row)
            self._current_row = []
        if tag == "li" and self._item_stack:
            text = compact(self._item_stack.pop())
            if "pharmacie" in normalize(text):
                self.items.append(text)
        if self._active_tags:
            self._active_tags.pop()

    def handle_data(self, data: str) -> None:
        if self._cell_stack:
            self._cell_stack[-1] += data
        if self._item_stack:
            self._item_stack[-1] += data


def row_to_entry(row: list[str]) -> dict[str, str]:
    details = " | ".join(row)
    name = next((cell for cell in row if "pharmacie" in normalize(cell)), row[0])
    phone_match = PHONE_PATTERN.search(details)
    phone = compact(phone_match.group(0)) if phone_match else ""

    city = ""
    region = ""
    for cell in row:
        text = normalize(cell)
        if not city and any(key in text for key in ("ville", "city")):
            city = cell
        if not region and "region" in text:
            region = cell

    return {
        "name": compact(name),
        "address": compact(row[1] if len(row) > 1 else ""),
        "city": compact(city),
        "region": compact(region),
        "phone": phone,
        "details": compact(details),
    }


def parse_guard_pharmacies(page_html: str) -> list[dict[str, str]]:
    parser = GuardPharmacyParser()
    parser.feed(page_html)

    entries: list[dict[str, str]] = []

    for row in parser.rows:
        if len(row) < 2:
            continue
        row_entry = row_to_entry(row)
        entries.append(row_entry)

    if not entries:
        for item in parser.items:
            if not item:
                continue
            phone_match = PHONE_PATTERN.search(item)
            phone = compact(phone_match.group(0)) if phone_match else ""
            entries.append(
                {
                    "name": item.split("-")[0].strip(),
                    "address": "",
                    "city": "",
                    "region": "",
                    "phone": phone,
                    "details": item,
                }
            )

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in entries:
        key = (
            normalize(entry.get("name", "")),
            normalize(entry.get("address", "")),
            normalize(entry.get("phone", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)

    return deduped


def fetch_guard_pharmacies() -> list[dict[str, str]]:
    request = Request(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; api-pharmacie/1.0)",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get_content_charset() or "utf-8"
            page_html = response.read().decode(content_type, errors="replace")
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Source inaccessible: {exc.reason}") from exc

    pharmacies = parse_guard_pharmacies(page_html)
    if not pharmacies:
        raise HTTPException(status_code=502, detail="Aucune pharmacie trouvée depuis la source")
    return pharmacies


def apply_filters(
    pharmacies: list[dict[str, str]],
    ville: str | None = None,
    region: str | None = None,
    autour: str | None = None,
) -> list[dict[str, str]]:
    if not (ville or region or autour):
        return pharmacies

    filters = [value for value in (ville, region, autour) if value]
    normalized_filters = [normalize(value or "") for value in filters]

    filtered: list[dict[str, str]] = []
    for pharmacy in pharmacies:
        haystack = normalize(" ".join(str(value) for value in pharmacy.values()))
        if all(filter_value in haystack for filter_value in normalized_filters):
            filtered.append(pharmacy)
    return filtered


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/pharmacies-de-garde")
def list_guard_pharmacies(
    ville: str | None = Query(default=None, description="Ville recherchée"),
    region: str | None = Query(default=None, description="Région recherchée"),
    autour: str | None = Query(default=None, description="Terme libre (quartier/environ)"),
) -> dict[str, Any]:
    normalized_ville = validate_filter_value(ville, CITY_MAP, "Ville")
    normalized_region = validate_filter_value(region, REGION_MAP, "Région")

    pharmacies = fetch_guard_pharmacies()
    filtered = apply_filters(
        pharmacies,
        ville=normalized_ville,
        region=normalized_region,
        autour=autour,
    )

    return {
        "source": SOURCE_URL,
        "filters": {"ville": normalized_ville, "region": normalized_region, "autour": autour},
        "available_filters": {"villes": AVAILABLE_CITIES, "regions": AVAILABLE_REGIONS},
        "count": len(filtered),
        "results": filtered,
    }


@app.get("/pharmacies-de-garde/filters")
def list_available_filters() -> dict[str, list[str]]:
    return {"villes": AVAILABLE_CITIES, "regions": AVAILABLE_REGIONS}
