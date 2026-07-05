"""Terminal WhatsApp draft outreach queue.

This opens WhatsApp Web draft URLs only. It never sends a message.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
import json
from pathlib import Path
import sys
import time
from urllib.parse import quote
import webbrowser

from lead_store import LEAD_COLUMNS, read_leads
from utils import clean_text, normalize_phone, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "outreach-config.json"
CONTACTED_CSV_PATH = BASE_DIR / "contacted.csv"
CONTACTED_JSON_PATH = BASE_DIR / "contacted.json"
DATA_CONTACTED_CSV_PATH = BASE_DIR / "data" / "contacted_clients.csv"

DEFAULT_CONFIG = {
    "dailyLimit": 20,
    "gapMinutes": 3,
    "messageTemplate": (
        "नमस्ते सर/मैडम, मी तुमच्या Classes साठी Professional Website / Landing Page बनवून देऊ शकतो. "
        "यामध्ये Online Admission Form, Course Details, Contact Button, WhatsApp Inquiry आणि Google Maps Location "
        "असे features असतील. जर तुम्हाला demo पाहायचा असेल तर मी पाठवू शकतो."
    ),
}

CONTACTED_COLUMNS = ["name", "phone", "city", "dateTime", "message", "status"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run WhatsApp draft outreach queue.")
    parser.add_argument("--dry-run", action="store_true", help="Show drafts without opening browser or saving contacted files.")
    parser.add_argument("--no-prompt", action="store_true", help="Do not wait for Enter before each draft.")
    args = parser.parse_args()

    config = load_config()
    daily_limit = max(int(config.get("dailyLimit") or 20), 1)
    gap_seconds = max(float(config.get("gapMinutes") or 3), 0) * 60
    template = clean_text(config.get("messageTemplate")) or DEFAULT_CONFIG["messageTemplate"]

    contacted_phones = read_contacted_phones()
    leads = unique_pending_leads(read_leads(), contacted_phones)
    queue_path = BASE_DIR / f"outreach-{date.today().isoformat()}.json"
    queue = load_or_create_queue(queue_path, leads, contacted_phones, daily_limit, template)

    completed = [item for item in queue["clients"] if item.get("status") in {"drafted", "contacted"}]
    pending = [item for item in queue["clients"] if item.get("status") in {"pending", "queued_today"}]
    print_header(queue_path, queue, len(completed), daily_limit, gap_seconds)

    if len(completed) >= daily_limit:
        print("Today's outreach limit is already complete.")
        return
    if not pending:
        print("No pending not_contacted leads found.")
        return

    for item in pending:
        completed_count = len([client for client in queue["clients"] if client.get("status") in {"drafted", "contacted"}])
        if completed_count >= daily_limit:
            break
        show_client(item, completed_count + 1, daily_limit)
        if not args.no_prompt:
            input("Press Enter to open WhatsApp draft for this client, or Ctrl+C to stop...")

        url = whatsapp_url(item["phone"], item["message"])
        print(f"Opening draft URL: {url}")
        if not args.dry_run:
            webbrowser.open(url)
            mark_drafted(item, queue, queue_path)
            append_contacted(item)
            contacted_phones.add(item["phone"])
        else:
            print("Dry run: not opening browser and not saving contacted files.")

        completed_count += 1
        if completed_count >= daily_limit:
            break
        if not args.dry_run:
            countdown(gap_seconds)

    final_completed = len([client for client in queue["clients"] if client.get("status") in {"drafted", "contacted"}])
    print(f"Done for today: {final_completed}/{daily_limit}")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
        return dict(DEFAULT_CONFIG)
    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        print("Invalid outreach-config.json. Using default config.", file=sys.stderr)
        return dict(DEFAULT_CONFIG)
    config = dict(DEFAULT_CONFIG)
    config.update(loaded)
    return config


def unique_pending_leads(leads: list[dict], contacted_phones: set[str]) -> list[dict]:
    by_phone: dict[str, dict] = {}
    for lead in leads:
        phone = normalize_phone(lead.get("phone"))
        status = clean_text(lead.get("whatsappStatus") or "not_contacted")
        if not phone or phone in contacted_phones or status != "not_contacted":
            continue
        if phone not in by_phone:
            clean_lead = {column: clean_text(lead.get(column)) for column in LEAD_COLUMNS}
            clean_lead["phone"] = phone
            by_phone[phone] = clean_lead
    return list(by_phone.values())


def load_or_create_queue(
    queue_path: Path,
    leads: list[dict],
    contacted_phones: set[str],
    daily_limit: int,
    template: str,
) -> dict:
    if queue_path.exists():
        try:
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            if isinstance(queue, dict) and isinstance(queue.get("clients"), list):
                existing_phones = {normalize_phone(item.get("phone")) for item in queue["clients"]}
                for item in queue["clients"]:
                    item["phone"] = normalize_phone(item.get("phone"))
                    if item["phone"] in contacted_phones and item.get("status") == "pending":
                        item["status"] = "contacted"
                for lead in leads:
                    if len(queue["clients"]) >= daily_limit:
                        break
                    if lead["phone"] not in existing_phones:
                        queue["clients"].append(queue_item(lead, template))
                        existing_phones.add(lead["phone"])
                write_json(queue_path, queue)
                return queue
        except json.JSONDecodeError:
            pass

    queue = {
        "date": date.today().isoformat(),
        "dailyLimit": daily_limit,
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "clients": [queue_item(lead, template) for lead in leads[:daily_limit]],
    }
    write_json(queue_path, queue)
    return queue


def queue_item(lead: dict, template: str) -> dict:
    message = render_message(template, lead)
    return {
        "name": clean_text(lead.get("name")),
        "phone": normalize_phone(lead.get("phone")),
        "city": clean_text(lead.get("city")),
        "status": "pending",
        "dateTime": "",
        "message": message,
    }


def render_message(template: str, lead: dict) -> str:
    values = {
        "name": clean_text(lead.get("name")),
        "className": clean_text(lead.get("name")),
        "city": clean_text(lead.get("city")),
        "phone": normalize_phone(lead.get("phone")),
    }
    message = template
    for key, value in values.items():
        message = message.replace("{" + key + "}", value)
    return message


def whatsapp_url(phone: str, message: str) -> str:
    normalized = normalize_phone(phone)
    if len(normalized) == 10:
        normalized = f"91{normalized}"
    return f"https://wa.me/{normalized}?text={quote(message)}"


def mark_drafted(item: dict, queue: dict, queue_path: Path) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    item["status"] = "drafted"
    item["dateTime"] = now
    write_json(queue_path, queue)


def append_contacted(item: dict) -> None:
    row = {
        "name": clean_text(item.get("name")),
        "phone": normalize_phone(item.get("phone")),
        "city": clean_text(item.get("city")),
        "dateTime": clean_text(item.get("dateTime")) or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": clean_text(item.get("message")),
        "status": clean_text(item.get("status")) or "drafted",
    }
    rows = read_contacted_rows()
    if row["phone"] not in {existing.get("phone") for existing in rows}:
        rows.append(row)
    write_contacted(rows)


def read_contacted_phones() -> set[str]:
    phones = {row["phone"] for row in read_contacted_rows() if row.get("phone")}
    if DATA_CONTACTED_CSV_PATH.exists():
        with DATA_CONTACTED_CSV_PATH.open("r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                phone = normalize_phone(row.get("phone"))
                if phone:
                    phones.add(phone)
    return phones


def read_contacted_rows() -> list[dict]:
    rows: list[dict] = []
    if CONTACTED_CSV_PATH.exists():
        with CONTACTED_CSV_PATH.open("r", newline="", encoding="utf-8-sig") as handle:
            rows.extend(canonical_contacted(row) for row in csv.DictReader(handle))
    elif CONTACTED_JSON_PATH.exists():
        try:
            payload = json.loads(CONTACTED_JSON_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                rows.extend(canonical_contacted(row) for row in payload if isinstance(row, dict))
        except json.JSONDecodeError:
            pass

    by_phone: dict[str, dict] = {}
    for row in rows:
        phone = row.get("phone", "")
        if phone and phone not in by_phone:
            by_phone[phone] = row
    return list(by_phone.values())


def canonical_contacted(row: dict) -> dict:
    return {
        "name": clean_text(row.get("name") or row.get("business_name")),
        "phone": normalize_phone(row.get("phone")),
        "city": clean_text(row.get("city") or row.get("district")),
        "dateTime": clean_text(row.get("dateTime") or row.get("contactedAt") or row.get("date_contacted")),
        "message": clean_text(row.get("message") or row.get("lastMessage")),
        "status": clean_text(row.get("status") or "drafted"),
    }


def write_contacted(rows: list[dict]) -> None:
    rows = sorted(rows, key=lambda row: row.get("dateTime", ""))
    temporary_path = CONTACTED_CSV_PATH.with_name(f"{CONTACTED_CSV_PATH.stem}.tmp{CONTACTED_CSV_PATH.suffix}")
    with temporary_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONTACTED_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(CONTACTED_CSV_PATH)
    CONTACTED_JSON_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def print_header(queue_path: Path, queue: dict, completed: int, daily_limit: int, gap_seconds: float) -> None:
    print("")
    print("WhatsApp Draft Outreach")
    print("=======================")
    print(f"Queue file: {queue_path.name}")
    print(f"Daily progress: {completed}/{daily_limit}")
    print(f"Gap: {int(gap_seconds // 60)} minute(s)")
    print("Safety: this opens a WhatsApp draft only. It does not send messages.")
    print("")


def show_client(item: dict, index: int, daily_limit: int) -> None:
    print("")
    print(f"Next client {index}/{daily_limit}")
    print(f"Name : {item.get('name') or 'Unknown'}")
    print(f"Phone: {item.get('phone')}")
    print(f"City : {item.get('city') or 'Unknown'}")
    print("Message:")
    print(item.get("message"))
    print("")


def countdown(seconds: float) -> None:
    total = int(seconds)
    if total <= 0:
        return
    while total > 0:
        minutes, remaining = divmod(total, 60)
        print(f"\rWaiting before next draft: {minutes:02d}:{remaining:02d}", end="", flush=True)
        time.sleep(1)
        total -= 1
    print("\rWaiting before next draft: 00:00")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOutreach stopped by user.")
