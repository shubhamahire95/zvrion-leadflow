"""Build safe, dynamic Google Maps search queries."""
import re


def build_query(niche: str, state: str, district: str, taluka: str = "", city: str = "") -> str:
    niche, state, district, taluka, city = (_clean(x) for x in (niche, state, district, taluka, city))
    if not niche:
        raise ValueError("Business type / niche is required.")
    if city:
        return f"{niche} in {city}, {district}, {state}"
    if taluka:
        return f"{niche} near {taluka}, {district}, {state}"
    return f"{niche} in {district}, {state}"


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" ,")
