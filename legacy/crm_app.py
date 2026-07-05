"""Local CRM follow-up web app for WhatsApp outreach.

Run:
    python crm_app.py
Then open:
    http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse
import webbrowser

from crm import (
    CRM_STATUSES,
    bootstrap_crm,
    crm_stats,
    export_rows,
    get_client,
    get_daily_queue,
    get_message_template,
    import_scraped_leads,
    mark_contacted,
    render_message,
    save_message_template,
    update_client,
)

HOST = "127.0.0.1"
PORT = 8765


class CRMHandler(BaseHTTPRequestHandler):
    server_version = "CoachingCRM/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(INDEX_HTML)
            return
        if parsed.path == "/api/bootstrap":
            self._send_json(bootstrap_crm())
            return
        if parsed.path == "/api/queue":
            self._send_json({"queue": get_daily_queue(), "stats": crm_stats()})
            return
        if parsed.path == "/api/template":
            self._send_json({"template": get_message_template()})
            return
        if parsed.path == "/api/export":
            params = parse_qs(parsed.query)
            export_type = params.get("type", ["contacted"])[0]
            file_format = params.get("format", ["csv"])[0]
            try:
                filename, payload, content_type = export_rows(export_type, file_format)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/import":
                imported = import_scraped_leads()
                self._send_json({"imported": imported, "stats": crm_stats(), "queue": get_daily_queue()})
                return
            if parsed.path == "/api/template":
                template = save_message_template(payload.get("template", ""))
                self._send_json({"template": template})
                return
            if parsed.path == "/api/render-message":
                client = get_client(payload.get("phone", ""))
                if not client:
                    self._send_json({"error": "Client not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_json({"message": render_message(get_message_template(), client)})
                return
            if parsed.path == "/api/contact":
                client = get_client(payload.get("phone", ""))
                if not client:
                    self._send_json({"error": "Client not found"}, HTTPStatus.NOT_FOUND)
                    return
                message = payload.get("message") or render_message(get_message_template(), client)
                updated = mark_contacted(client["phone"], message)
                self._send_json(
                    {
                        "client": updated,
                        "queue": get_daily_queue(),
                        "stats": crm_stats(),
                        "whatsappUrl": f"https://wa.me/91{updated['phone']}?text={quote(message)}",
                    }
                )
                return
            if parsed.path == "/api/client":
                updated = update_client(payload.get("phone", ""), payload)
                self._send_json({"client": updated, "queue": get_daily_queue(), "stats": crm_stats()})
                return
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        print("%s - %s" % (self.address_string(), format % args))

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Coaching Leads CRM</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #617080;
      --line: #d9e0e7;
      --brand: #176b5c;
      --brand-dark: #0f5145;
      --danger: #b42318;
      --warn: #a16207;
      --good: #167647;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 4;
    }
    h1 { margin: 0; font-size: 22px; letter-spacing: 0; }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 18px;
      padding: 18px;
      max-width: 1440px;
      margin: 0 auto;
    }
    .toolbar, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      width: 100%;
    }
    .stat {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfd;
    }
    .stat b { display: block; font-size: 22px; }
    .stat span { color: var(--muted); font-size: 12px; }
    .queue-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }
    .progress-wrap {
      flex: 1;
      min-width: 220px;
    }
    .progress-label {
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }
    .bar { height: 10px; background: #e8edf1; border-radius: 999px; overflow: hidden; }
    .bar > div { height: 100%; background: var(--brand); width: 0; }
    .lead-list { display: grid; gap: 10px; }
    .lead {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
    }
    .lead h2 { margin: 0 0 6px; font-size: 17px; }
    .meta { color: var(--muted); font-size: 13px; line-height: 1.45; }
    .actions { display: flex; align-items: start; gap: 8px; flex-wrap: wrap; justify-content: end; }
    button, select, textarea, input {
      font: inherit;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
    }
    button {
      cursor: pointer;
      padding: 9px 12px;
      font-weight: 650;
    }
    button.primary { background: var(--brand); border-color: var(--brand); color: #fff; }
    button.primary:hover { background: var(--brand-dark); }
    button.ghost { background: #f8fafb; }
    button:disabled { cursor: not-allowed; opacity: .55; }
    select, input { padding: 8px 10px; }
    textarea {
      width: 100%;
      min-height: 180px;
      padding: 10px;
      line-height: 1.45;
      resize: vertical;
    }
    .panel { padding: 14px; margin-bottom: 14px; }
    .panel h2 { margin: 0 0 10px; font-size: 16px; }
    .side-actions { display: grid; gap: 8px; }
    .side-actions a {
      display: block;
      color: var(--brand-dark);
      text-decoration: none;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      background: #fbfcfd;
    }
    .message-preview {
      white-space: pre-wrap;
      background: #f8fafb;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      min-height: 90px;
      color: #26323f;
    }
    .status {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 700;
      background: #eef2f6;
      color: #344054;
    }
    .status.interested, .status.replied { background: #dcfae6; color: var(--good); }
    .status.not_interested, .status.opt_out { background: #fee4e2; color: var(--danger); }
    .status.contacted { background: #fef0c7; color: var(--warn); }
    .small { color: var(--muted); font-size: 12px; }
    .notice { color: var(--muted); font-size: 13px; margin-top: 8px; }
    @media (max-width: 960px) {
      main { grid-template-columns: 1fr; }
      .stats { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      .lead { grid-template-columns: 1fr; }
      .actions { justify-content: start; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Coaching Leads CRM</h1>
    <div>
      <button class="ghost" id="importBtn">Refresh Leads</button>
      <button class="primary" id="reloadBtn">Reload Queue</button>
    </div>
  </header>
  <main>
    <section>
      <div class="toolbar">
        <div class="stats">
          <div class="stat"><b id="totalStat">0</b><span>Total clients</span></div>
          <div class="stat"><b id="pendingStat">0</b><span>Pending</span></div>
          <div class="stat"><b id="contactedStat">0</b><span>Contacted</span></div>
          <div class="stat"><b id="replyStat">0</b><span>Replied / interested</span></div>
        </div>
      </div>
      <div class="panel">
        <div class="queue-head">
          <div>
            <h2>Daily Outreach Queue</h2>
            <div class="small" id="queueDate">Today</div>
          </div>
          <div class="progress-wrap">
            <div class="progress-label"><span id="progressText">0/20</span><span id="cooldownText">Ready</span></div>
            <div class="bar"><div id="progressBar"></div></div>
          </div>
        </div>
        <div id="leadList" class="lead-list"></div>
      </div>
    </section>
    <aside>
      <div class="panel">
        <h2>Message Template</h2>
        <textarea id="templateBox"></textarea>
        <div class="notice">Variables: {className}, {city}, {ownerName}</div>
        <p><button class="primary" id="saveTemplateBtn">Save Template</button></p>
      </div>
      <div class="panel">
        <h2>Selected Message</h2>
        <div id="previewBox" class="message-preview">Select a client to preview the message.</div>
      </div>
      <div class="panel">
        <h2>Exports</h2>
        <div class="side-actions">
          <a href="/api/export?type=contacted&format=csv">Contacted clients CSV</a>
          <a href="/api/export?type=contacted&format=xlsx">Contacted clients Excel</a>
          <a href="/api/export?type=pending&format=csv">Pending clients CSV</a>
          <a href="/api/export?type=pending&format=xlsx">Pending clients Excel</a>
          <a href="/api/export?type=replied_interested&format=csv">Replied/interested CSV</a>
          <a href="/api/export?type=replied_interested&format=xlsx">Replied/interested Excel</a>
        </div>
      </div>
    </aside>
  </main>
  <script>
    const state = { queue: null, stats: null, template: "", selectedPhone: "", cooldownUntil: Number(localStorage.getItem("crmCooldownUntil") || 0) };
    const statuses = ["not_contacted", "contacted", "replied", "interested", "not_interested", "opt_out"];
    const $ = (id) => document.getElementById(id);

    async function api(path, options = {}) {
      const res = await fetch(path, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Request failed");
      return data;
    }

    async function load() {
      const data = await api("/api/bootstrap");
      state.queue = data.queue;
      state.stats = data.stats;
      state.template = data.template;
      $("templateBox").value = data.template;
      render();
    }

    function render() {
      renderStats();
      renderQueue();
      tickCooldown();
    }

    function renderStats() {
      const s = state.stats || {};
      $("totalStat").textContent = s.total || 0;
      $("pendingStat").textContent = s.pending || 0;
      $("contactedStat").textContent = s.contacted || 0;
      $("replyStat").textContent = s.repliedInterested || 0;
    }

    function renderQueue() {
      const q = state.queue || { clients: [], completed: 0, limit: 20 };
      $("queueDate").textContent = q.date || "Today";
      $("progressText").textContent = `${q.completed || 0}/${q.limit || 20}`;
      $("progressBar").style.width = `${Math.min(100, ((q.completed || 0) / (q.limit || 20)) * 100)}%`;
      const list = $("leadList");
      list.innerHTML = "";
      if (!q.clients.length) {
        list.innerHTML = '<div class="small">No eligible pending clients found. Refresh leads after a scraper run.</div>';
        return;
      }
      q.clients.forEach((client, index) => {
        const card = document.createElement("article");
        card.className = "lead";
        card.innerHTML = `
          <div>
            <h2>${escapeHtml(index + 1)}. ${escapeHtml(client.business_name || "Unnamed class")}</h2>
            <div class="meta">
              ${escapeHtml(client.phone || "")} | ${escapeHtml(client.city || client.taluka || client.district || "")}<br>
              ${escapeHtml(client.category || "")}<br>
              ${escapeHtml(client.full_address || "")}
            </div>
            <p><span class="status ${escapeHtml(client.whatsappStatus)}">${escapeHtml(client.whatsappStatus)}</span></p>
            <textarea data-notes="${escapeHtml(client.phone)}" placeholder="Notes">${escapeHtml(client.notes || "")}</textarea>
          </div>
          <div class="actions">
            <button class="ghost" data-preview="${escapeHtml(client.phone)}">Preview</button>
            <button class="primary send-btn" data-send="${escapeHtml(client.phone)}">Send/Open WhatsApp</button>
            <select data-status="${escapeHtml(client.phone)}">
              ${statuses.map(status => `<option value="${status}" ${status === client.whatsappStatus ? "selected" : ""}>${status}</option>`).join("")}
            </select>
            <button class="ghost" data-save="${escapeHtml(client.phone)}">Save</button>
          </div>
        `;
        list.appendChild(card);
      });
      bindLeadActions();
    }

    function bindLeadActions() {
      document.querySelectorAll("[data-preview]").forEach(btn => btn.onclick = () => preview(btn.dataset.preview));
      document.querySelectorAll("[data-send]").forEach(btn => btn.onclick = () => sendWhatsApp(btn.dataset.send));
      document.querySelectorAll("[data-save]").forEach(btn => btn.onclick = () => saveClient(btn.dataset.save));
      tickCooldown();
    }

    async function preview(phone) {
      state.selectedPhone = phone;
      const data = await api("/api/render-message", { method: "POST", body: JSON.stringify({ phone }) });
      $("previewBox").textContent = data.message;
    }

    async function sendWhatsApp(phone) {
      if (remainingCooldown() > 0) return;
      const data = await api("/api/render-message", { method: "POST", body: JSON.stringify({ phone }) });
      const contact = await api("/api/contact", { method: "POST", body: JSON.stringify({ phone, message: data.message }) });
      state.queue = contact.queue;
      state.stats = contact.stats;
      state.cooldownUntil = Date.now() + 180000;
      localStorage.setItem("crmCooldownUntil", String(state.cooldownUntil));
      window.open(contact.whatsappUrl, "_blank", "noopener");
      render();
    }

    async function saveClient(phone) {
      const status = document.querySelector(`[data-status="${cssEscape(phone)}"]`).value;
      const notes = document.querySelector(`[data-notes="${cssEscape(phone)}"]`).value;
      const data = await api("/api/client", { method: "POST", body: JSON.stringify({ phone, whatsappStatus: status, notes }) });
      state.queue = data.queue;
      state.stats = data.stats;
      render();
    }

    function remainingCooldown() {
      return Math.max(0, state.cooldownUntil - Date.now());
    }

    function tickCooldown() {
      const remaining = remainingCooldown();
      const buttons = document.querySelectorAll(".send-btn");
      if (remaining <= 0) {
        $("cooldownText").textContent = "Ready";
        buttons.forEach(btn => btn.disabled = false);
        return;
      }
      const seconds = Math.ceil(remaining / 1000);
      const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
      const ss = String(seconds % 60).padStart(2, "0");
      $("cooldownText").textContent = `Next client in ${mm}:${ss}`;
      buttons.forEach(btn => btn.disabled = true);
    }

    setInterval(tickCooldown, 1000);

    $("saveTemplateBtn").onclick = async () => {
      const data = await api("/api/template", { method: "POST", body: JSON.stringify({ template: $("templateBox").value }) });
      state.template = data.template;
      if (state.selectedPhone) await preview(state.selectedPhone);
    };
    $("reloadBtn").onclick = async () => {
      const data = await api("/api/queue");
      state.queue = data.queue;
      state.stats = data.stats;
      render();
    };
    $("importBtn").onclick = async () => {
      const data = await api("/api/import", { method: "POST", body: "{}" });
      state.queue = data.queue;
      state.stats = data.stats;
      render();
    };

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
    }
    function cssEscape(value) {
      if (window.CSS && CSS.escape) return CSS.escape(value);
      return String(value).replace(/"/g, '\\"');
    }

    load().catch(err => {
      $("leadList").innerHTML = `<div class="small">${escapeHtml(err.message)}</div>`;
    });
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local CRM follow-up UI.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    bootstrap_crm()
    server = ThreadingHTTPServer((args.host, args.port), CRMHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"CRM follow-up app running at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
