"""File-backed CRM follow-up workflow for scraped coaching leads."""

from __future__ import annotations

import csv
from datetime import date, datetime
from io import BytesIO, StringIO
import json
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook

from utils import clean_text, normalize_phone, write_json

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
CRM_CLIENTS_PATH = DATA_DIR / "crm_clients.csv"
CONTACTED_CLIENTS_PATH = DATA_DIR / "contacted_clients.csv"
QUEUE_PATH = DATA_DIR / "daily_outreach_queues.json"
TEMPLATE_PATH = DATA_DIR / "message_template.txt"
CRM_EXPORT_DIR = BASE_DIR / "crm_exports"

CRM_STATUSES = {
    "not_contacted",
    "contacted",
    "replied",
    "interested",
    "not_interested",
    "opt_out",
}
CONTACTED_STATUSES = {"contacted", "replied", "interested", "not_interested", "opt_out"}
FINAL_EXCLUDED_STATUSES = {"not_interested", "opt_out"}
QUEUE_SIZE = 20

CRM_COLUMNS = [
    "phone",
    "business_name",
    "ownerName",
    "category",
    "district",
    "taluka",
    "city",
    "full_address",
    "rating",
    "reviews",
    "website",
    "maps_link",
    "source_file",
    "whatsappStatus",
    "contactedAt",
    "lastMessage",
    "notes",
    "optOut",
    "updatedAt",
]
CONTACTED_COLUMNS = [
    "phone",
    "business_name",
    "date_contacted",
    "status",
    "contactedAt",
    "lastMessage",
    "notes",
    "district",
    "city",
]

DEFAULT_MESSAGE_TEMPLATE = """Namaste {ownerName},

Mi {className} sathi ek professional website/Google presence improve karanyabaddal contact karat aahe. Aaplya classes la online students enquiries vadhavnyasathi simple website ani WhatsApp lead setup madat karu shakto.

City: {city}

Interested asal tar mi short demo share karto."""


def bootstrap_crm() -> dict:
    """Import current scraped leads and return CRM dashboard data."""
    DATA_DIR.mkdir(exist_ok=True)
    CRM_EXPORT_DIR.mkdir(exist_ok=True)
    _ensure_csv(CRM_CLIENTS_PATH, CRM_COLUMNS)
    _ensure_csv(CONTACTED_CLIENTS_PATH, CONTACTED_COLUMNS)
    _ensure_template()
    imported = import_scraped_leads()
    return {
        "imported": imported,
        "stats": crm_stats(),
        "queue": get_daily_queue(),
        "template": get_message_template(),
    }


def import_scraped_leads(output_dir: Path = OUTPUT_DIR) -> int:
    """Merge exported lead CSVs into CRM state, deduping by normalized phone."""
    existing = _read_crm_rows()
    contacted_statuses = _read_contacted_statuses()
    for row in existing:
        phone = row.get("phone", "")
        if phone in contacted_statuses and row.get("whatsappStatus") == "not_contacted":
            row["whatsappStatus"] = contacted_statuses[phone]
            row["contactedAt"] = row.get("contactedAt") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    by_phone = {row["phone"]: row for row in existing if row.get("phone")}
    imported = 0

    for path in _lead_csv_paths(output_dir):
        for raw in _read_csv(path):
            row = _canonical_lead_row(raw, path)
            phone = row.get("phone", "")
            if not phone or phone in by_phone:
                continue
            if phone in contacted_statuses:
                row["whatsappStatus"] = contacted_statuses[phone]
                row["contactedAt"] = row.get("contactedAt") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            by_phone[phone] = row
            imported += 1

    _write_crm_rows(by_phone.values())
    return imported


def crm_stats() -> dict:
    rows = _read_crm_rows()
    counts = {status: 0 for status in sorted(CRM_STATUSES)}
    for row in rows:
        status = _safe_status(row.get("whatsappStatus"))
        counts[status] = counts.get(status, 0) + 1
    return {
        "total": len(rows),
        "pending": len(_pending_rows(rows)),
        "contacted": len([row for row in rows if row.get("whatsappStatus") in CONTACTED_STATUSES]),
        "repliedInterested": len(
            [row for row in rows if row.get("whatsappStatus") in {"replied", "interested"}]
        ),
        "counts": counts,
    }


def get_daily_queue(queue_date: str | None = None) -> dict:
    queue_date = queue_date or date.today().isoformat()
    rows = _read_crm_rows()
    by_phone = {row["phone"]: row for row in rows if row.get("phone")}
    queues = _read_json(QUEUE_PATH, {})

    phones = [phone for phone in queues.get(queue_date, []) if _queue_eligible_phone(phone, by_phone)]
    if queue_date not in queues or len(phones) < min(QUEUE_SIZE, len(_pending_rows(rows))):
        selected = list(phones)
        for row in _pending_rows(rows):
            phone = row["phone"]
            if phone in selected:
                continue
            selected.append(phone)
            if len(selected) >= QUEUE_SIZE:
                break
        phones = selected[:QUEUE_SIZE]
        queues[queue_date] = phones
        write_json(QUEUE_PATH, queues)

    queue_rows = [by_phone[phone] for phone in phones if phone in by_phone]
    completed = len([row for row in queue_rows if row.get("whatsappStatus") != "not_contacted"])
    return {
        "date": queue_date,
        "limit": QUEUE_SIZE,
        "completed": completed,
        "remaining": max(len(queue_rows) - completed, 0),
        "clients": queue_rows,
    }


def get_client(phone: str) -> dict | None:
    normalized = normalize_phone(phone)
    for row in _read_crm_rows():
        if row.get("phone") == normalized:
            return row
    return None


def mark_contacted(phone: str, message: str) -> dict:
    normalized = normalize_phone(phone)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = _read_crm_rows()
    updated: dict | None = None
    for row in rows:
        if row.get("phone") != normalized:
            continue
        if row.get("whatsappStatus") in FINAL_EXCLUDED_STATUSES:
            updated = row
            break
        row["whatsappStatus"] = "contacted"
        row["contactedAt"] = row.get("contactedAt") or now
        row["lastMessage"] = clean_text(message)
        row["updatedAt"] = now
        row["optOut"] = ""
        updated = row
        break
    if updated is None:
        raise ValueError("Client not found")
    _write_crm_rows(rows)
    _sync_contacted_clients(rows)
    return updated


def update_client(phone: str, updates: dict) -> dict:
    normalized = normalize_phone(phone)
    rows = _read_crm_rows()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated: dict | None = None
    for row in rows:
        if row.get("phone") != normalized:
            continue
        if "whatsappStatus" in updates:
            row["whatsappStatus"] = _safe_status(updates.get("whatsappStatus"))
            if row["whatsappStatus"] in FINAL_EXCLUDED_STATUSES:
                row["optOut"] = "yes"
        for key in ["notes", "lastMessage", "ownerName"]:
            if key in updates:
                row[key] = clean_text(updates.get(key))
        row["updatedAt"] = now
        updated = row
        break
    if updated is None:
        raise ValueError("Client not found")
    _write_crm_rows(rows)
    _sync_contacted_clients(rows)
    return updated


def get_message_template() -> str:
    _ensure_template()
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def save_message_template(template: str) -> str:
    DATA_DIR.mkdir(exist_ok=True)
    TEMPLATE_PATH.write_text(str(template).strip() + "\n", encoding="utf-8")
    return get_message_template()


def render_message(template: str, client: dict) -> str:
    values = {
        "className": clean_text(client.get("business_name")),
        "city": clean_text(client.get("city") or client.get("taluka") or client.get("district")),
        "ownerName": clean_text(client.get("ownerName")) or "Sir/Madam",
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def export_rows(kind: str, file_format: str) -> tuple[str, bytes, str]:
    rows = _rows_for_export(kind)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kind = kind.replace("-", "_")
    if file_format == "xlsx":
        filename = f"{safe_kind}_{timestamp}.xlsx"
        return filename, _xlsx_bytes(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    filename = f"{safe_kind}_{timestamp}.csv"
    return filename, _csv_bytes(rows), "text/csv; charset=utf-8"


def _rows_for_export(kind: str) -> list[dict]:
    rows = _read_crm_rows()
    if kind == "contacted":
        return [row for row in rows if row.get("whatsappStatus") in CONTACTED_STATUSES]
    if kind == "pending":
        return _pending_rows(rows)
    if kind in {"replied_interested", "replied-interested"}:
        return [row for row in rows if row.get("whatsappStatus") in {"replied", "interested"}]
    raise ValueError("Unknown export type")


def _lead_csv_paths(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []
    names = {"HOT_LEADS.csv", "hot_leads.csv", "NEW_PROSPECTS.csv", "all_data.csv", "ALL_DATA.csv"}
    return sorted(path for path in output_dir.rglob("*.csv") if path.name in names)


def _canonical_lead_row(raw: dict, source_path: Path) -> dict:
    phone = normalize_phone(_first(raw, "phone", "Phone", "WhatsApp", "whatsapp"))
    status = _safe_status(_first(raw, "whatsappStatus", "WhatsApp Status") or "not_contacted")
    opt_out = clean_text(_first(raw, "optOut", "Opt Out"))
    if status in FINAL_EXCLUDED_STATUSES:
        opt_out = "yes"
    return {
        "phone": phone,
        "business_name": clean_text(_first(raw, "business_name", "Business Name")),
        "ownerName": clean_text(_first(raw, "ownerName", "Owner Name")),
        "category": clean_text(_first(raw, "category", "Category")),
        "district": clean_text(_first(raw, "district", "District")),
        "taluka": clean_text(_first(raw, "taluka", "Taluka")),
        "city": clean_text(_first(raw, "city", "City")),
        "full_address": clean_text(_first(raw, "full_address", "Address")),
        "rating": clean_text(_first(raw, "rating", "Rating")),
        "reviews": clean_text(_first(raw, "reviews", "Reviews")),
        "website": clean_text(_first(raw, "website", "Website")),
        "maps_link": clean_text(_first(raw, "maps_link", "Maps URL")),
        "source_file": str(source_path.relative_to(BASE_DIR)) if source_path.is_relative_to(BASE_DIR) else str(source_path),
        "whatsappStatus": status,
        "contactedAt": clean_text(_first(raw, "contactedAt", "Contacted At")),
        "lastMessage": clean_text(_first(raw, "lastMessage", "Last Message")),
        "notes": clean_text(_first(raw, "notes", "Notes")),
        "optOut": opt_out,
        "updatedAt": "",
    }


def _pending_rows(rows: Iterable[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("phone")
        and row.get("whatsappStatus") == "not_contacted"
        and row.get("whatsappStatus") not in FINAL_EXCLUDED_STATUSES
        and clean_text(row.get("optOut")).casefold() not in {"yes", "true", "1"}
    ]


def _queue_eligible_phone(phone: str, by_phone: dict[str, dict]) -> bool:
    row = by_phone.get(phone)
    if not row:
        return False
    return row.get("whatsappStatus") not in FINAL_EXCLUDED_STATUSES


def _safe_status(value: object) -> str:
    status = clean_text(value).casefold()
    return status if status in CRM_STATUSES else "not_contacted"


def _read_crm_rows() -> list[dict]:
    _ensure_csv(CRM_CLIENTS_PATH, CRM_COLUMNS)
    rows = []
    for row in _read_csv(CRM_CLIENTS_PATH):
        normalized = {column: clean_text(row.get(column)) for column in CRM_COLUMNS}
        normalized["phone"] = normalize_phone(normalized.get("phone"))
        normalized["whatsappStatus"] = _safe_status(normalized.get("whatsappStatus"))
        if normalized["phone"]:
            rows.append(normalized)
    return _dedupe_rows(rows)


def _write_crm_rows(rows: Iterable[dict]) -> None:
    unique = _dedupe_rows(rows)
    unique.sort(key=lambda row: (row.get("whatsappStatus") != "not_contacted", row.get("district"), row.get("business_name")))
    _write_csv(CRM_CLIENTS_PATH, unique, CRM_COLUMNS)


def _sync_contacted_clients(rows: Iterable[dict]) -> None:
    contacted = []
    for row in rows:
        if row.get("whatsappStatus") not in CONTACTED_STATUSES:
            continue
        contacted.append(
            {
                "phone": row.get("phone", ""),
                "business_name": row.get("business_name", ""),
                "date_contacted": clean_text(row.get("contactedAt"))[:10],
                "status": row.get("whatsappStatus", ""),
                "contactedAt": row.get("contactedAt", ""),
                "lastMessage": row.get("lastMessage", ""),
                "notes": row.get("notes", ""),
                "district": row.get("district", ""),
                "city": row.get("city", ""),
            }
        )
    _write_csv(CONTACTED_CLIENTS_PATH, contacted, CONTACTED_COLUMNS)


def _read_contacted_statuses() -> dict[str, str]:
    statuses: dict[str, str] = {}
    if not CONTACTED_CLIENTS_PATH.exists():
        return statuses
    for row in _read_csv(CONTACTED_CLIENTS_PATH):
        phone = normalize_phone(row.get("phone"))
        if not phone:
            continue
        statuses[phone] = _safe_status(row.get("status") or "contacted")
        if statuses[phone] == "not_contacted":
            statuses[phone] = "contacted"
    return statuses


def _dedupe_rows(rows: Iterable[dict]) -> list[dict]:
    by_phone: dict[str, dict] = {}
    for row in rows:
        phone = normalize_phone(row.get("phone"))
        if not phone:
            continue
        normalized = {column: clean_text(row.get(column)) for column in CRM_COLUMNS}
        normalized["phone"] = phone
        normalized["whatsappStatus"] = _safe_status(normalized.get("whatsappStatus"))
        if phone not in by_phone:
            by_phone[phone] = normalized
            continue
        existing = by_phone[phone]
        for column in CRM_COLUMNS:
            if not existing.get(column) and normalized.get(column):
                existing[column] = normalized[column]
        if _status_rank(normalized.get("whatsappStatus")) > _status_rank(existing.get("whatsappStatus")):
            existing["whatsappStatus"] = normalized["whatsappStatus"]
    return list(by_phone.values())


def _status_rank(status: object) -> int:
    order = {
        "not_contacted": 0,
        "contacted": 1,
        "replied": 2,
        "interested": 3,
        "not_interested": 4,
        "opt_out": 5,
    }
    return order.get(_safe_status(status), 0)


def _csv_bytes(rows: list[dict]) -> bytes:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CRM_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _xlsx_bytes(rows: list[dict]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "CRM_EXPORT"
    worksheet.append(CRM_COLUMNS)
    for row in rows:
        worksheet.append([row.get(column, "") for column in CRM_COLUMNS])
    for column in worksheet.columns:
        letter = column[0].column_letter
        max_width = max(len(clean_text(cell.value)) for cell in column)
        worksheet.column_dimensions[letter].width = min(max(max_width + 3, 12), 52)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _ensure_template() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not TEMPLATE_PATH.exists():
        TEMPLATE_PATH.write_text(DEFAULT_MESSAGE_TEMPLATE + "\n", encoding="utf-8")


def _ensure_csv(path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _upgrade_csv(path, columns)
        return
    _write_csv(path, [], columns)


def _upgrade_csv(path: Path, columns: list[str]) -> None:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        current_columns = reader.fieldnames or []
        rows = list(reader)
    if current_columns == columns:
        return
    if any(column not in current_columns for column in columns):
        _write_csv(path, rows, columns)


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Iterable[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    with temporary_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: clean_text(row.get(column)) for column in columns})
    temporary_path.replace(path)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _first(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if clean_text(value):
            return clean_text(value)
    return ""
