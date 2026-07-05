"""JSON-backed, extensible India location helpers."""
import json

from config import LOCATIONS_FILE


def load_locations() -> dict:
    try:
        value = json.loads(LOCATIONS_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def states() -> list[str]:
    return sorted(load_locations(), key=str.casefold)


def districts(state: str) -> list[str]:
    return sorted(load_locations().get(state, {}), key=str.casefold)


def talukas(state: str, district: str) -> list[str]:
    value = load_locations().get(state, {}).get(district, {})
    return sorted(value if isinstance(value, dict) else [], key=str.casefold)


def cities(state: str, district: str, taluka: str) -> list[str]:
    value = load_locations().get(state, {}).get(district, {}).get(taluka, [])
    return value if isinstance(value, list) else []


def validate_location(state: str, district: str, taluka: str = "", city: str = ""):
    state, district, taluka, city = (str(x or "").strip() for x in (state, district, taluka, city))
    if not state:
        raise ValueError("State is required.")
    if not district:
        raise ValueError("District is required.")
    known = load_locations()
    if state not in known:
        raise ValueError("Please select a valid state.")
    if known[state] and district not in known[state]:
        raise ValueError("Please select a valid district for the state.")
    return state, district, taluka, city
