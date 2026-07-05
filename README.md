# ZVRION LeadFlow

ZVRION LeadFlow is a local Google Maps lead-generation dashboard. It runs Playwright in a background job, shows live progress and business previews, filters results, and exports CSV/XLSX/JSON files. It does not send WhatsApp messages, run outreach, or use a paid API.

## Setup

Python 3.10+ is recommended.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Local run

Web dashboard:

```powershell
python web_app.py
```

Open <http://127.0.0.1:8765>.

CLI example:

```powershell
python app.py --niche "classes" --state Maharashtra --district Nashik --taluka Yeola --city Yeola --max-results 10 --json
```

For the safest first test, keep all discovered businesses even when Maps does not publish a phone:

```powershell
python app.py --niche "classes" --state Maharashtra --district Nashik --city Yeola --max-results 10 --no-phone-required --json
```

## How to scrape

Open **New Scrape**, choose a preset niche (or Custom), select a required state and district, and optionally narrow the search to a taluka or city. Choose the filters and press **Start scraping**. The job continues in the background while **Live Leads** shows its query, progress, raw/clean counts, filter-by-filter cleaner summary, and latest businesses.

If city is empty, LeadFlow searches the selected taluka. If both city and taluka are empty, it searches the full district.

## Files, history, and downloads

Exports are saved under `output/` as:

```text
zvrion_leads_<niche>_<location>_<timestamp>.csv
zvrion_leads_<niche>_<location>_<timestamp>.xlsx
zvrion_leads_<niche>_<location>_<timestamp>.json
```

Every completed or failed web run is recorded in `data/history.json`. The **History** section shows run details and export links. The **Downloads** section lists every file currently in `output/`, including its creation time and size. Location choices are maintained in `data/locations.json`.

Every scrape also writes `debug_raw_<timestamp>.json`. Rejected records are saved as `rejected_leads_<timestamp>.json` with a `rejection_reason`. If an export is unexpectedly empty, inspect the Live Leads cleaner summary and rerun with **Phone required** or **Website missing only** disabled as indicated.

## Main API

- `POST /api/jobs/start`
- `GET /api/jobs/<job_id>/status`
- `GET /api/jobs/<job_id>/results`
- `GET /api/history`
- `GET /api/downloads`
- `GET /api/download/<filename>`
- `GET /api/preview/<filename>`
- `DELETE /api/downloads/<filename>`

## Hosting note

The app uses project-relative `pathlib` paths and Flask downloads. For hosting, run `web_app:app` behind a production WSGI server, persist `data/` and `output/`, and use a worker setup suitable for long-running Playwright jobs. The in-memory job registry is intended for a single app process; use a durable queue such as Redis/RQ or Celery before scaling to multiple workers.
