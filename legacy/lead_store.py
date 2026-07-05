"""Root lead store used by scraper and terminal outreach."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from utils import clean_text, normalize_phone

BASE_DIR = Path(__file__).resolve().parent
LEADS_CSV_PATH = BASE_DIR / "leads.csv"
LEADS_JSON_PATH = BASE_DIR / "leads.json"

LEAD_COLUMNS = [
    "name",
    "phone",
    "city",
    "district",
    "taluka",
    "category",
    "address",
    "rating",
    "reviews",
    "website",
    "maps_link",
    "whatsappStatus",
    "contactedAt",
    "lastMessage",
    "notes",
]


def save_leads(rows: Iterable[dict]) -> int:
    """Merge new scraped rows into root leads.csv and leads.json by phone."""
    existing = _read_leads()
    by_phone = {row["phone"]: row for row in existing if row.get("phone")}
    added = 0

    for raw in rows:
        row = _canonical_lead(raw)
        phone = row.get("phone", "")
        if not phone:
            continue
        if phone in by_phone:
            _merge_missing(by_phone[phone], row)
            continue
        by_phone[phone] = row
        added += 1

    merged = sorted(by_phone.values(), key=lambda row: (row.get("district", ""), row.get("city", ""), row.get("name", "")))
    _write_csv(LEADS_CSV_PATH, merged)
    LEADS_JSON_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return added


def read_leads() -> list[dict]:
    return _read_leads()


def _read_leads() -> list[dict]:
    rows: list[dict] = []
    if LEADS_CSV_PATH.exists():
        with LEADS_CSV_PATH.open("r", newline="", encoding="utf-8-sig") as handle:
            rows.extend(_canonical_lead(row) for row in csv.DictReader(handle))
    elif LEADS_JSON_PATH.exists():
        try:
            payload = json.loads(LEADS_JSON_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                rows.extend(_canonical_lead(row) for row in payload if isinstance(row, dict))
        except json.JSONDecodeError:
            pass

    by_phone: dict[str, dict] = {}
    for row in rows:
        phone = row.get("phone", "")
        if not phone:
            continue
        if phone not in by_phone:
            by_phone[phone] = row
        else:
            _merge_missing(by_phone[phone], row)
    return list(by_phone.values())


def _canonical_lead(raw: dict) -> dict:
    name = _first(raw, "name", "business_name", "Business Name")
    city = _first(raw, "city", "City")
    taluka = _first(raw, "taluka", "Taluka")
    district = _first(raw, "district", "District")
    return {
        "name": clean_text(name),
        "phone": normalize_phone(_first(raw, "phone", "Phone", "whatsapp", "WhatsApp", "Phone Number")),
        "city": clean_text(city or taluka or district),
        "district": clean_text(district),
        "taluka": clean_text(taluka),
        "category": clean_text(_first(raw, "category", "Category", "search_query", "Search Query")),
        "address": clean_text(_first(raw, "address", "full_address", "Address")),
        "rating": clean_text(_first(raw, "rating", "Rating")),
        "reviews": clean_text(_first(raw, "reviews", "Reviews", "Reviews Count")),
        "website": clean_text(_first(raw, "website", "Website")),
        "maps_link": clean_text(_first(raw, "maps_link", "Maps URL")),
        "whatsappStatus": clean_text(_first(raw, "whatsappStatus", "WhatsApp Status") or "not_contacted"),
        "contactedAt": clean_text(_first(raw, "contactedAt", "Contacted At")),
        "lastMessage": clean_text(_first(raw, "lastMessage", "Last Message")),
        "notes": clean_text(_first(raw, "notes", "Notes")),
    }


def _merge_missing(target: dict, incoming: dict) -> None:
    for column in LEAD_COLUMNS:
        if not target.get(column) and incoming.get(column):
            target[column] = incoming[column]


def _write_csv(path: Path, rows: list[dict]) -> None:
    temporary_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    with temporary_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEAD_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(path)


def _first(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if clean_text(value):
            return clean_text(value)
    return ""
