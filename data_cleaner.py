"""Normalize, filter, deduplicate, and explain Google Maps lead decisions."""
import re
from typing import Iterable
from config import OUTPUT_COLUMNS


def normalize_phone(value: object) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("0") and len(digits) == 11: digits = digits[1:]
    if digits.startswith("91") and len(digits) == 12: digits = digits[2:]
    if len(digits) == 10 and digits[0] in "6789": return f"+91{digits}"
    return f"+{digits}" if 7 <= len(digits) <= 15 else ""


def clean_business_name(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" -|,\n\t")


def _rating(value):
    if value in (None, ""): return None
    try: return float(str(value).replace(",", "."))
    except (TypeError, ValueError): return None


def clean_leads(records: Iterable[dict], min_rating: float = 0, phone_required: bool = True,
                no_website_only: bool = False, return_details: bool = False):
    rows = list(records); output, rejected, seen_phones, seen_maps = [], [], set(), set()
    summary = {"raw_count": len(rows), "after_phone_filter": 0, "after_rating_filter": 0,
               "after_website_filter": 0, "after_dedup": 0, "rejected_count": 0,
               "missing_phone_count": 0, "low_rating_count": 0, "website_present_count": 0,
               "duplicate_count": 0, "missing_name_count": 0}
    phone_pass, rating_pass, website_pass = [], [], []
    for raw in rows:
        item = dict(raw); item["phone"] = normalize_phone(raw.get("phone"))
        if phone_required and not item["phone"]:
            item["rejection_reason"] = "missing_phone"; rejected.append(item); summary["missing_phone_count"] += 1
        else: phone_pass.append(item)
    summary["after_phone_filter"] = len(phone_pass)
    for item in phone_pass:
        rating = _rating(item.get("rating"))
        # A missing Maps rating is unknown, not zero. Only known low ratings are rejected.
        if rating is not None and rating < min_rating:
            item["rejection_reason"] = "rating_below_minimum"; rejected.append(item); summary["low_rating_count"] += 1
        else:
            item["rating"] = rating if rating is not None else ""; rating_pass.append(item)
    summary["after_rating_filter"] = len(rating_pass)
    for item in rating_pass:
        if no_website_only and str(item.get("website") or "").strip():
            item["rejection_reason"] = "website_present"; rejected.append(item); summary["website_present_count"] += 1
        else: website_pass.append(item)
    summary["after_website_filter"] = len(website_pass)
    for item in website_pass:
        phone = item["phone"]; maps_link = str(item.get("maps_link") or "").strip().split("&")[0]
        name = clean_business_name(item.get("business_name"))
        if not name:
            item["rejection_reason"] = "missing_business_name"; rejected.append(item); summary["missing_name_count"] += 1; continue
        if (phone and phone in seen_phones) or (maps_link and maps_link in seen_maps):
            item["rejection_reason"] = "duplicate"; rejected.append(item); summary["duplicate_count"] += 1; continue
        row = {column: item.get(column, "") for column in OUTPUT_COLUMNS}
        row.update(business_name=name, phone=phone, whatsapp_phone=phone, maps_link=maps_link)
        output.append(row)
        if phone: seen_phones.add(phone)
        if maps_link: seen_maps.add(maps_link)
    summary["after_dedup"] = len(output); summary["rejected_count"] = len(rejected)
    return (output, rejected, summary) if return_details else output


def empty_result_message(summary, phone_required=False, no_website_only=False):
    if summary["raw_count"] == 0: return "No Google Maps listings were collected for this query."
    if phone_required and summary["after_phone_filter"] == 0:
        return f"{summary['raw_count']} found, 0 exported because phone numbers were not available. Try unchecking Phone required."
    if summary["after_rating_filter"] == 0:
        return f"{summary['raw_count']} found, 0 exported because all known ratings were below the minimum."
    if no_website_only and summary["after_website_filter"] == 0:
        return f"{summary['raw_count']} found, 0 exported because every listing had a website. Try unchecking Website missing only."
    return f"{summary['raw_count']} found, 0 exported after validation and duplicate removal. Check the rejected debug file."
