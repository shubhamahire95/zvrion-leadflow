"""Prepare a one-page WhatsApp draft list without opening WhatsApp."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import webbrowser

from lead_store import read_leads
from outreach import (
    BASE_DIR,
    append_contacted,
    load_config,
    load_or_create_queue,
    queue_item,
    read_contacted_phones,
    unique_pending_leads,
    whatsapp_url,
)
from utils import normalize_phone, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HOST = "127.0.0.1"
PORT = 8766


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare today's WhatsApp draft HTML list.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true", help="Do not open the generated HTML page.")
    args = parser.parse_args()

    config = load_config()
    daily_limit = max(int(config.get("dailyLimit") or 20), 1)
    template = str(config.get("messageTemplate") or "")

    contacted_phones = read_contacted_phones()
    leads = unique_pending_leads(read_leads(), contacted_phones)
    queue_path = BASE_DIR / f"outreach-{date.today().isoformat()}.json"
    html_path = BASE_DIR / f"drafts-{date.today().isoformat()}.html"
    queue = load_or_create_queue(queue_path, leads, contacted_phones, daily_limit, template)
    queue["mode"] = "prepare_drafts"

    selected = []
    existing_phones = {normalize_phone(item.get("phone")) for item in queue.get("clients", [])}
    for item in queue.get("clients", []):
        if len(selected) >= daily_limit:
            break
        phone = normalize_phone(item.get("phone"))
        if phone in contacted_phones:
            item["status"] = "sent"
            continue
        if item.get("status") in {"contacted", "sent"}:
            continue
        item["status"] = "queued_today"
        selected.append(item)
    for lead in leads:
        if len(selected) >= daily_limit:
            break
        if lead["phone"] in existing_phones:
            continue
        item = queue_item(lead, template)
        item["status"] = "queued_today"
        queue["clients"].append(item)
        selected.append(item)
        existing_phones.add(lead["phone"])

    queue["clients"] = selected
    write_json(queue_path, queue)
    html_path.write_text(render_html(selected, args.host, args.port), encoding="utf-8")

    print("")
    print("Prepare Draft List")
    print("==================")
    print(f"HTML file : {html_path}")
    print(f"Queue file: {queue_path}")
    print(f"Clients   : {len(selected)}/{daily_limit}")
    print("No WhatsApp drafts were opened automatically.")
    print("")
    print(f"Open this URL while this terminal stays running: http://{args.host}:{args.port}/{html_path.name}")
    print("Use 'Mark Sent' in the page after you manually send a WhatsApp draft.")
    print("")

    server = DraftServer((args.host, args.port), DraftHandler, queue_path)
    if not args.no_browser:
        webbrowser.open(f"http://{args.host}:{args.port}/{html_path.name}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPrepare drafts server stopped.")


class DraftServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, queue_path: Path):
        super().__init__(server_address, handler_class)
        self.queue_path = queue_path


class DraftHandler(BaseHTTPRequestHandler):
    server_version = "PrepareDrafts/1.0"

    def do_GET(self) -> None:
        requested = self.path.split("?", 1)[0].lstrip("/") or f"drafts-{date.today().isoformat()}.html"
        if requested != f"drafts-{date.today().isoformat()}.html":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        html_path = BASE_DIR / requested
        if not html_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = html_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/mark-sent":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            phone = normalize_phone(payload.get("phone"))
            queue = json.loads(self.server.queue_path.read_text(encoding="utf-8"))
            item = find_queue_item(queue, phone)
            if item is None:
                self._send_json({"error": "Client not found"}, HTTPStatus.NOT_FOUND)
                return
            item["status"] = "sent"
            item["dateTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            write_json(self.server.queue_path, queue)
            append_contacted(item)
            self._send_json({"ok": True, "phone": phone, "dateTime": item["dateTime"]})
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args) -> None:
        print("%s - %s" % (self.address_string(), format % args))

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def find_queue_item(queue: dict, phone: str) -> dict | None:
    for item in queue.get("clients", []):
        if normalize_phone(item.get("phone")) == phone:
            return item
    return None


def render_html(clients: list[dict], host: str, port: int) -> str:
    rows = "\n".join(render_client_card(client, index + 1) for index, client in enumerate(clients))
    if not rows:
        rows = '<div class="empty">No not_contacted clients available for today.</div>'
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WhatsApp Drafts {date.today().isoformat()}</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #f6f7f9; color: #17202a; }}
    header {{ padding: 18px 22px; background: #fff; border-bottom: 1px solid #d9e0e7; position: sticky; top: 0; }}
    h1 {{ margin: 0 0 6px; font-size: 22px; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 18px; display: grid; gap: 12px; }}
    .card {{ background: #fff; border: 1px solid #d9e0e7; border-radius: 8px; padding: 14px; }}
    .top {{ display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }}
    h2 {{ margin: 0 0 6px; font-size: 18px; }}
    .meta {{ color: #617080; line-height: 1.45; }}
    .message {{ white-space: pre-wrap; background: #f8fafb; border: 1px solid #d9e0e7; border-radius: 6px; padding: 10px; margin: 12px 0; }}
    .actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    button, a.button {{ border: 1px solid #176b5c; border-radius: 6px; padding: 9px 12px; font-weight: 650; cursor: pointer; text-decoration: none; display: inline-block; }}
    a.button {{ background: #176b5c; color: #fff; }}
    button {{ background: #fff; color: #176b5c; }}
    button.sent {{ background: #dcfae6; border-color: #167647; color: #167647; }}
    .empty {{ background: #fff; border: 1px solid #d9e0e7; border-radius: 8px; padding: 18px; color: #617080; }}
  </style>
</head>
<body>
  <header>
    <h1>WhatsApp Draft List - {date.today().isoformat()}</h1>
    <div>Open WhatsApp manually, copy if needed, then click Mark Sent only after you send.</div>
  </header>
  <main>{rows}</main>
  <script>
    async function copyMessage(id) {{
      const text = document.getElementById(id).innerText;
      await navigator.clipboard.writeText(text);
      alert("Message copied");
    }}
    async function markSent(phone, button) {{
      const res = await fetch("http://{host}:{port}/mark-sent", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ phone }})
      }});
      const data = await res.json();
      if (!res.ok) {{
        alert(data.error || "Could not save contacted file. Keep npm run prepare-drafts running.");
        return;
      }}
      button.classList.add("sent");
      button.textContent = "Sent Saved";
      button.disabled = true;
    }}
  </script>
</body>
</html>
"""


def render_client_card(client: dict, index: int) -> str:
    message_id = f"message-{index}"
    phone = normalize_phone(client.get("phone"))
    message = str(client.get("message") or "")
    status = str(client.get("status") or "queued_today")
    sent = status in {"sent", "contacted", "drafted"}
    sent_attrs = ' class="sent" disabled' if sent else ""
    sent_label = "Sent Saved" if sent else "Mark Sent"
    return f"""<section class="card">
  <div class="top">
    <div>
      <h2>{index}. {escape(str(client.get("name") or "Unknown"))}</h2>
      <div class="meta">Phone: {escape(phone)}<br>City: {escape(str(client.get("city") or "Unknown"))}<br>Status: {escape(status)}</div>
    </div>
    <div class="actions">
      <a class="button" href="{escape(whatsapp_url(phone, message), quote=True)}" target="_blank" rel="noopener">Open WhatsApp Draft</a>
      <button type="button" onclick="copyMessage('{message_id}')">Copy Message</button>
      <button type="button"{sent_attrs} onclick="markSent('{escape(phone)}', this)">{sent_label}</button>
    </div>
  </div>
  <div id="{message_id}" class="message">{escape(message)}</div>
</section>"""


if __name__ == "__main__":
    main()
