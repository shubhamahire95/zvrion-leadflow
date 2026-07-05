"""CLI entry point and shared lead-generation pipeline."""
import argparse, logging
from data_cleaner import clean_leads, empty_result_message
from exporter import export_debug, export_leads
from location_manager import validate_location
from query_builder import build_query
from scraper import GoogleMapsScraper


def run_pipeline(*, niche, state, district, taluka="", city="", min_rating=0, max_results=50,
                 headless=True, phone_required=True, no_website_only=False, include_json=False,
                 status_callback=None):
    if not 0 <= min_rating <= 5: raise ValueError("Minimum rating must be between 0 and 5.")
    if not 1 <= max_results <= 500: raise ValueError("Maximum results must be between 1 and 500.")
    state, district, taluka, city = validate_location(state, district, taluka, city)
    query = build_query(niche, state, district, taluka, city)
    notify = status_callback or (lambda **_: None)
    notify(stage="searching", message="Searching Google Maps", progress=5, query=query)
    raw = GoogleMapsScraper(headless=headless).scrape(query, max_results, notify)
    for row in raw: row.update(city=city, taluka=taluka, district=district, state=state)
    notify(stage="cleaning", message="Cleaning and filtering leads", progress=86,
           total_raw=len(raw), preview=raw[-10:])
    leads, rejected, summary = clean_leads(raw, min_rating, phone_required, no_website_only, return_details=True)
    notify(stage="exporting", message="Creating export files", progress=94,
           total_raw=len(raw), total_clean=len(leads), preview=leads[-10:], summary=summary)
    location = city or taluka or district
    # Never publish a header-only CSV/XLSX as a successful lead export.
    paths = export_leads(leads, niche, location, include_json=include_json) if leads else {}
    paths.update(export_debug(raw, rejected))
    message = "" if leads else empty_result_message(summary, phone_required, no_website_only)
    return leads, raw, paths, query, summary, message


def parse_args():
    parser = argparse.ArgumentParser(description="Generate business leads from Google Maps without paid APIs.")
    parser.add_argument("--niche", required=True); parser.add_argument("--state", default="Maharashtra")
    parser.add_argument("--district", required=True); parser.add_argument("--taluka", default="")
    parser.add_argument("--city", default=""); parser.add_argument("--min-rating", type=float, default=0.0)
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--phone-required", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--no-website-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="Also create JSON output")
    return parser.parse_args()


def main():
    args = parse_args(); logging.basicConfig(level=logging.INFO)
    def status(**update): print(f"[{update.get('progress', 0)}%] {update.get('message', '')}")
    options = vars(args).copy(); options["include_json"] = options.pop("json")
    leads, _raw, paths, query, summary, message = run_pipeline(**options, status_callback=status)
    print(f"\nQuery: {query}\nClean leads: {len(leads)}")
    print(f"Cleaner summary: {summary}")
    if message: print(message)
    for kind, path in paths.items(): print(f"{kind.upper()}: {path}")


if __name__ == "__main__": main()
