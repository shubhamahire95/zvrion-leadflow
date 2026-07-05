"""Advanced duplicate removal for coaching lead records."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from data_transformer import transform_record
from utils import clean_text, normalize_business_name, normalize_phone


@dataclass(slots=True)
class DeduplicationResult:
    records: list[dict]
    total_businesses: int
    unique_businesses: int
    duplicates_removed: int


def record_dedupe_key(record: dict) -> str:
    keys = record_dedupe_keys(record)
    return keys[0] if keys else "empty:"


def record_dedupe_keys(record: dict) -> list[str]:
    keys: list[str] = []
    phone = normalize_phone(record.get("phone") or record.get("whatsapp") or record.get("mobile_number") or record.get("Phone Number"))
    name = _dedupe_text(record.get("business_name") or record.get("Business Name"))
    district = clean_text(record.get("district") or record.get("District")).casefold()

    if name and phone:
        keys.append(f"name-phone:{name}|{phone}")
    elif name and district:
        keys.append(f"name-district:{name}|{district}")
    return keys


def _dedupe_text(value: object) -> str:
    text = clean_text(value).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return clean_text(text)


def deduplicate_records(records: Iterable[dict]) -> DeduplicationResult:
    total = 0
    unique_records: list[dict] = []
    key_index: dict[str, int] = {}

    for raw_record in records:
        total += 1
        record = transform_record(dict(raw_record))
        if not clean_text(record.get("business_name")):
            continue

        keys = record_dedupe_keys(record)
        existing_indexes = [key_index[key] for key in keys if key in key_index]
        if not existing_indexes:
            unique_records.append(record)
            record_index = len(unique_records) - 1
            for key in keys:
                key_index[key] = record_index
            continue

        record_index = existing_indexes[0]
        existing = unique_records[record_index]
        _merge_record(existing, record)
        for key in record_dedupe_keys(existing):
            key_index[key] = record_index

    return DeduplicationResult(
        records=unique_records,
        total_businesses=total,
        unique_businesses=len(unique_records),
        duplicates_removed=max(total - len(unique_records), 0),
    )


def _merge_record(existing: dict, incoming: dict) -> None:
    for field in ["mobile_number", "coaching_type", "rating", "reviews", "website", "full_address", "short_address", "district", "taluka", "city", "maps_link"]:
        if not clean_text(existing.get(field)) and clean_text(incoming.get(field)):
            existing[field] = incoming[field]

    _merge_csv_field(existing, incoming, "coaching_type")


def _merge_csv_field(existing: dict, incoming: dict, field: str) -> None:
    values = []
    for record in [existing, incoming]:
        for value in clean_text(record.get(field)).split(","):
            value = clean_text(value)
            if value and value not in values:
                values.append(value)
    if values:
        existing[field] = ", ".join(values)
