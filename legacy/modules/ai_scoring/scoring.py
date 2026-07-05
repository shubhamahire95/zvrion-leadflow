"""Deterministic premium lead scoring.

The scoring is intentionally local and explainable so long scans can run
without external API cost or network dependencies.
"""

from __future__ import annotations

import re

from utils import clean_text

PREMIUM_COLUMNS = [
    "business_name",
    "category",
    "rating",
    "reviews",
    "phone",
    "whatsapp",
    "full_address",
    "district",
    "taluka",
    "city",
    "maps_link",
    "website",
    "has_website",
    "lead_score",
    "premium_lead",
    "branch_count",
    "digital_presence",
    "rejection_reason",
]

TARGET_NICHE_PATTERN = re.compile(
    r"\b(iit\s*jee|jee|neet|mht\s*cet|11th|12th|hsc|ssc|spoken english|english speaking|ielts|toefl|music)\b",
    re.I,
)
KEYWORD_PATTERN = re.compile(r"\b(academy|institute|classes|class|coaching|tutorials)\b", re.I)
BRANCH_PATTERN = re.compile(r"\b(branch|branches|campus|centre|center|main branch|franchise)\b", re.I)
DIGITAL_PRESENCE_PATTERN = re.compile(
    r"\b(instagram\.com|facebook\.com|fb\.com|youtube\.com|youtu\.be|linktr\.ee|justdial|business\.site|sites\.google\.com)\b",
    re.I,
)


def score_premium_lead(row: dict) -> dict:
    name = clean_text(row.get("business_name") or row.get("Business Name"))
    category = clean_text(row.get("coaching_type") or row.get("Search Query"))
    address = clean_text(row.get("full_address") or row.get("short_address") or row.get("Address"))
    website = clean_text(row.get("website") or row.get("Website"))
    mobile = clean_text(row.get("mobile_number") or row.get("Phone Number"))
    rating = _to_float(row.get("rating") or row.get("Rating"))
    reviews = _to_int(row.get("reviews") or row.get("Reviews Count"))
    haystack = f"{name} {category} {address}".lower()

    score = 0
    reasons: list[str] = []
    if website or DIGITAL_PRESENCE_PATTERN.search(website):
        reasons.append("website or digital presence found")
        return {"score": 0, "priority": "REJECT", "reasons": reasons}
    if rating >= 4.2:
        score += 20
        reasons.append("strong rating")
    if reviews >= 20:
        score += 15
        reasons.append("20+ reviews")
    score += 25
    reasons.append("no website")
    if mobile:
        score += 15
        reasons.append("mobile/WhatsApp reachable")
    if TARGET_NICHE_PATTERN.search(haystack) and KEYWORD_PATTERN.search(haystack):
        score += 15
        reasons.append("target coaching niche")
    if BRANCH_PATTERN.search(haystack):
        score += 10
        reasons.append("possible multiple branches")

    score = max(0, min(score, 100))
    priority = "HOT" if score >= 70 else "WARM" if score >= 45 else "LOW"
    return {"score": score, "priority": priority, "reasons": reasons}


def build_premium_lead_row(row: dict) -> dict:
    scoring = score_premium_lead(row)
    mobile = clean_text(row.get("phone") or row.get("mobile_number"))
    rating = _to_float(row.get("rating") or row.get("Rating"))
    reviews = _to_int(row.get("reviews") or row.get("Reviews Count"))
    branch_count = 2 if BRANCH_PATTERN.search(f"{row.get('business_name')} {row.get('full_address')}") else 1
    return {
        "business_name": clean_text(row.get("business_name")),
        "category": clean_text(row.get("coaching_type") or row.get("category")),
        "rating": rating or "",
        "reviews": reviews or "",
        "phone": mobile,
        "whatsapp": mobile,
        "full_address": clean_text(row.get("full_address") or row.get("short_address")),
        "district": clean_text(row.get("district")),
        "taluka": clean_text(row.get("taluka")),
        "city": clean_text(row.get("city")),
        "maps_link": clean_text(row.get("maps_link")),
        "website": clean_text(row.get("website")),
        "has_website": "yes" if clean_text(row.get("website")) else "no",
        "lead_score": scoring["score"],
        "premium_lead": "yes" if scoring["score"] >= 70 and rating >= 4.5 and reviews >= 20 else "no",
        "branch_count": branch_count,
        "digital_presence": "website" if clean_text(row.get("website")) else "none_found",
        "rejection_reason": "" if scoring["score"] >= 70 else "; ".join(scoring["reasons"]),
    }


def _to_float(value: object) -> float:
    try:
        return float(clean_text(value))
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: object) -> int:
    text = re.sub(r"\D+", "", clean_text(value))
    return int(text) if text else 0
