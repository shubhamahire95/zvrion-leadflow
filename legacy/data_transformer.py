"""Transform raw Google Maps records into coaching lead export rows."""

from __future__ import annotations

import re

from location_manager import get_district_for_location
from utils import clean_text, normalize_phone

COACHING_TYPE_RULES = [
    ("MHT CET", ["mht cet", "mh cet"]),
    ("IIT JEE", ["iit jee", "jee", "iit"]),
    ("NEET", ["neet"]),
    ("HSC Board", ["hsc board", "hsc classes", "12th science", "11th 12th science"]),
    ("SSC Board", ["ssc board", "ssc classes", "10th classes"]),
    ("Spoken English", ["spoken english", "english speaking"]),
    ("IELTS TOEFL", ["ielts", "toefl"]),
    ("Science", ["science academy", "science classes", "physics", "chemistry", "biology"]),
    ("Music Classes", ["music classes", "music academy", "music school"]),
]


def transform_record(record: dict) -> dict:
    business_name = clean_text(record.get("business_name") or record.get("Business Name"))
    category = clean_text(record.get("coaching_type") or record.get("Search Query"))
    description = clean_text(record.get("Description") or record.get("Searches Found In"))
    address = clean_text(record.get("full_address") or record.get("address") or record.get("short_address") or record.get("Address"))

    district = clean_text(record.get("district") or record.get("District") or _location_value(record, "district"))
    taluka = clean_text(record.get("taluka") or record.get("Taluka") or _location_value(record, "taluka"))
    city = clean_text(record.get("city") or record.get("City") or _location_value(record, "city"))
    district = district or get_district_for_location(taluka, "taluka") or get_district_for_location(city, "city")

    return {
        "business_name": business_name,
        "mobile_number": normalize_phone(record.get("mobile_number") or record.get("Phone Number")),
        "coaching_type": detect_coaching_type(business_name, category, description),
        "rating": clean_text(record.get("rating") or record.get("Rating")),
        "reviews": clean_text(record.get("reviews") or record.get("Reviews Count")),
        "website": clean_text(record.get("website") or record.get("Website")),
        "full_address": address,
        "short_address": extract_short_address(address),
        "district": district,
        "taluka": taluka,
        "city": city,
        "maps_link": clean_text(record.get("maps_link") or record.get("Maps URL")),
    }


def detect_coaching_type(title: str, category: str, description: str = "") -> str:
    haystack = f" {title} {category} {description} ".casefold()
    matches: list[str] = []
    for coaching_type, keywords in COACHING_TYPE_RULES:
        if any(keyword in haystack for keyword in keywords):
            matches.append(coaching_type)
    return ", ".join(dict.fromkeys(matches)) or clean_text(category) or "Coaching"


def extract_short_address(address: str) -> str:
    text = clean_text(address)
    if not text:
        return ""

    text = re.sub(r"\bMaharashtra\b.*$", "", text, flags=re.IGNORECASE).strip(" ,")
    text = re.sub(r"\bIndia\b.*$", "", text, flags=re.IGNORECASE).strip(" ,")
    text = re.sub(r"\b\d{6}\b", "", text).strip(" ,")
    parts = [clean_text(part) for part in text.split(",") if clean_text(part)]
    filtered = [
        part
        for part in parts
        if not re.search(r"\b(near|opposite|opp\.?|floor|building|shop|plot|road|lane|behind)\b", part, re.IGNORECASE)
    ]
    useful = filtered[-2:] if len(filtered) >= 2 else parts[-2:]
    return ", ".join(useful)


def _location_value(record: dict, expected_type: str) -> str:
    location_type = clean_text(record.get("Location Type")).lower()
    if location_type == expected_type:
        return clean_text(record.get("City"))
    if expected_type == "city" and not location_type:
        return clean_text(record.get("City"))
    return ""
