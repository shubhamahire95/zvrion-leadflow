"""Shared helpers for scraping, normalization, and durable progress files."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PHONE_DIGITS_PATTERN = re.compile(r"\D+")
BUSINESS_SUFFIX_PATTERN = re.compile(
    r"\b(classes|class|coaching|tutorials|tutorial|academy|institute|institutes|centre|center|educational|education|pvt|ltd|llp|school|branch)\b",
    re.IGNORECASE,
)
BRANCH_WORD_PATTERN = re.compile(
    r"\b(main|branch|campus|centre|center|near|opp|opposite|road|rd|nagar|colony|chowk|circle|market|west|east|north|south)\b",
    re.IGNORECASE,
)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def normalize_phone(value: object) -> str:
    digits = PHONE_DIGITS_PATTERN.sub("", clean_text(value))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_website(value: object) -> str:
    text = clean_text(value).lower()
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    parsed = urlparse(text)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def normalize_business_name(value: object) -> str:
    text = clean_text(value).lower()
    text = BUSINESS_SUFFIX_PATTERN.sub(" ", text)
    text = BRANCH_WORD_PATTERN.sub(" ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return clean_text(text)


def normalize_maps_url(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""

    parsed = urlparse(text)
    path = parsed.path.rstrip("/")
    query = parse_qs(parsed.query)
    place_id = query.get("cid", [""])[0] or query.get("ftid", [""])[0]
    if place_id:
        return f"maps:{place_id.lower()}"
    return f"{parsed.netloc.lower().replace('www.', '')}{path.lower()}"


def normalize_query_key(city: str, category: str) -> str:
    return f"{clean_text(city).lower()}::{clean_text(category).lower()}"


def read_json(path: str | Path, default):
    file_path = Path(path)
    if not file_path.exists():
        return default
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: str | Path, payload: object) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: str | Path, payload: dict) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_jsonl(path: str | Path) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        return []

    records: list[dict] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records
