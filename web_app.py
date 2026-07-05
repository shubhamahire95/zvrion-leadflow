"""ZVRION LeadFlow Flask dashboard and background scraping API."""
from __future__ import annotations
import json, logging, threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from flask import Flask, abort, jsonify, render_template, request, send_file, url_for
from app import run_pipeline
from config import DATA_DIR, HISTORY_FILE, HOST, OUTPUT_DIR, PORT
from location_manager import cities, districts, states, talukas

app = Flask(__name__, template_folder="templates", static_folder="static")
JOBS: dict[str, dict] = {}; JOB_LOCK = threading.Lock(); HISTORY_LOCK = threading.Lock()


def job_response(*, success=False, job_id="", message="", status="idle", progress=0,
                 raw_count=0, clean_count=0, current_query="", preview=None, files=None, error=None,
                 cleaner_summary=None):
    """The single public response contract for all job endpoints."""
    return {"success": bool(success), "job_id": str(job_id), "message": str(message),
            "status": status, "progress": int(progress), "raw_count": int(raw_count),
            "clean_count": int(clean_count), "current_query": str(current_query),
            "preview": list(preview or []),
            "files": {"csv": None, "xlsx": None, "json": None, "debug_raw": None, "rejected": None} | (files or {}),
            "cleaner_summary": cleaner_summary or {}, "error": None if error is None else str(error)}


def read_history():
    try:
        value = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError): return []


def save_history(entry):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY_LOCK:
        rows = read_history(); rows.insert(0, entry)
        HISTORY_FILE.write_text(json.dumps(rows[:200], ensure_ascii=False, indent=2), encoding="utf-8")


def write_history(rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY_LOCK:
        HISTORY_FILE.write_text(json.dumps(rows[:200], ensure_ascii=False, indent=2), encoding="utf-8")


def parse_form(form):
    checked = lambda key: form.get(key) in (True, "true", "on", "1")
    options = {"niche": str(form.get("niche", "")).strip(), "state": str(form.get("state", "")).strip(),
               "district": str(form.get("district", "")).strip(), "taluka": str(form.get("taluka", "")).strip(),
               "city": str(form.get("city", "")).strip(), "min_rating": float(form.get("min_rating", 0)),
               "max_results": int(form.get("max_results", 50)), "phone_required": checked("phone_required"),
               "no_website_only": checked("no_website_only"), "include_json": checked("include_json")}
    if not options["niche"]: raise ValueError("Business niche is required.")
    if not options["state"] or not options["district"]: raise ValueError("State and district are required.")
    return options


def download_urls(paths):
    return {kind: f"/api/download/{path.name}" for kind, path in paths.items()}


def history_entry(job_id, options, raw, clean, paths, status, error=None):
    return {"id": job_id, "date_time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "niche": options.get("niche", ""), "state": options.get("state", ""),
            "district": options.get("district", ""), "taluka": options.get("taluka", ""),
            "city": options.get("city", ""), "min_rating": options.get("min_rating", 0),
            "max_results": options.get("max_results", 0), "phone_required": bool(options.get("phone_required")),
            "no_website_only": bool(options.get("no_website_only")), "total_raw": raw, "total_clean": clean,
            "csv_file": paths.get("csv").name if paths.get("csv") else "",
            "xlsx_file": paths.get("xlsx").name if paths.get("xlsx") else "",
            "json_file": paths.get("json").name if paths.get("json") else "",
            "status": status, "error": None if error is None else str(error)}


def run_job(job_id, options):
    def update(**values):
        with JOB_LOCK:
            current = JOBS[job_id]
            current.update(status="running", message=values.get("message", current["message"]),
                           progress=values.get("progress", current["progress"]),
                           raw_count=values.get("total_raw", current["raw_count"]),
                           clean_count=values.get("total_clean", current["clean_count"]),
                           current_query=values.get("query", current["current_query"]),
                           preview=values.get("preview", current["preview"]),
                           cleaner_summary=values.get("summary", current["cleaner_summary"]))
    try:
        leads, raw, paths, query, summary, empty_message = run_pipeline(**options, status_callback=update)
        files = download_urls(paths)
        save_history(history_entry(job_id, options, len(raw), len(leads), paths, "completed"))
        message = empty_message or f"Completed - {len(leads)} clean leads ready."
        completed = job_response(success=True, job_id=job_id, message=message,
                                 status="completed", progress=100, raw_count=len(raw), clean_count=len(leads),
                                 current_query=query, preview=leads[-20:], files=files, cleaner_summary=summary)
        with JOB_LOCK: JOBS[job_id] = completed | {"_results": leads}
    except Exception as exc:
        logging.exception("Scrape job %s failed", job_id)
        with JOB_LOCK: snapshot = JOBS.get(job_id, {})
        save_history(history_entry(job_id, options, snapshot.get("raw_count", 0), 0, {}, "error", exc))
        failed = job_response(job_id=job_id, message="Scraping failed.", status="error",
                              progress=snapshot.get("progress", 0), raw_count=snapshot.get("raw_count", 0),
                              current_query=snapshot.get("current_query", ""), preview=snapshot.get("preview", []), error=exc)
        with JOB_LOCK: JOBS[job_id] = failed | {"_results": []}


def public_job(job_id):
    with JOB_LOCK: job = JOBS.get(job_id)
    if not job: return None
    return {key: value for key, value in job.items() if not key.startswith("_")}


@app.get("/")
def index(): return render_template("index.html")

@app.get("/favicon.ico")
def favicon(): return app.send_static_file("favicon.svg")

@app.get("/api/states")
def api_states(): return jsonify(states())

@app.get("/api/districts")
def api_districts(): return jsonify(districts(request.args.get("state", "")))

@app.get("/api/talukas")
def api_talukas(): return jsonify(talukas(request.args.get("state", ""), request.args.get("district", "")))

@app.get("/api/cities")
def api_cities(): return jsonify(cities(request.args.get("state", ""), request.args.get("district", ""), request.args.get("taluka", "")))

@app.post("/api/jobs/start")
def start_job():
    form = request.get_json(silent=True) or request.form.to_dict(); job_id = uuid4().hex
    try:
        options = parse_form(form)
        queued = job_response(job_id=job_id, message="Scrape queued. Starting browser...", status="running", progress=1)
        with JOB_LOCK: JOBS[job_id] = queued | {"_results": []}
        threading.Thread(target=run_job, args=(job_id, options), daemon=True).start()
        return jsonify(queued), 202
    except (TypeError, ValueError) as exc:
        return jsonify(job_response(job_id=job_id, message="Please correct the form.", status="error", error=exc)), 400

@app.get("/api/jobs/<job_id>/status")
def job_status(job_id):
    job = public_job(job_id)
    if not job: return jsonify(job_response(job_id=job_id, message="Job not found.", status="error", error="Unknown job id")), 404
    return jsonify(job)

@app.get("/api/jobs/<job_id>/results")
def job_results(job_id):
    with JOB_LOCK: job = JOBS.get(job_id)
    if not job: return jsonify(job_response(job_id=job_id, message="Job not found.", status="error", error="Unknown job id")), 404
    response = public_job(job_id); response["preview"] = list(job.get("_results", []))
    return jsonify(response)

@app.delete("/api/jobs/<job_id>/leads")
def delete_job_leads(job_id):
    """Remove selected leads from both the live preview and the job's real result state."""
    keys = {str(value) for value in (request.get_json(silent=True) or {}).get("keys", [])}
    if not keys:
        return jsonify({"success": False, "message": "No leads selected."}), 400

    def lead_key(row):
        return str(row.get("_lead_id") or row.get("place_id") or
                   f"{row.get('business_name', '')}|{row.get('phone', '')}|{row.get('address', '')}")

    with JOB_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"success": False, "message": "Job not found."}), 404
        results = list(job.get("_results", []))
        kept = [row for row in results if lead_key(row) not in keys]
        removed = len(results) - len(kept)
        job["_results"] = kept
        job["preview"] = kept
        job["clean_count"] = len(kept)
    return jsonify({"success": True, "message": f"Deleted {removed} leads.", "clean_count": len(kept)})

@app.get("/api/history")
def api_history():
    rows = []
    for item in read_history()[:100]:
        row = dict(item); row["files"] = {kind: f"/api/download/{item.get(f'{kind}_file')}"
            if item.get(f"{kind}_file") else None for kind in ("csv", "xlsx", "json")}; rows.append(row)
    return jsonify(rows)

@app.delete("/api/history/<run_id>")
def delete_history(run_id):
    rows = read_history(); kept = [row for row in rows if row.get("id") != run_id]
    if len(kept) == len(rows): return jsonify({"success": False, "message": "History entry not found."}), 404
    write_history(kept); return jsonify({"success": True, "message": "History entry deleted."})

@app.delete("/api/history")
def clear_history():
    write_history([]); return jsonify({"success": True, "message": "History cleared."})

@app.get("/api/downloads")
def api_downloads():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True); rows = []
    for path in sorted((p for p in OUTPUT_DIR.iterdir() if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = path.stat(); parts = path.stem.split("_")
        niche = parts[2].replace("-", " ") if len(parts) > 4 and parts[:2] == ["zvrion", "leads"] else "Debug export"
        location = parts[3].replace("-", " ") if len(parts) > 4 and parts[:2] == ["zvrion", "leads"] else "—"
        rows.append({"name": path.name, "created": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
                     "size": stat.st_size, "niche": niche.title(), "location": location.title(),
                     "url": f"/api/download/{path.name}", "preview_url": f"/api/preview/{path.name}"})
    return jsonify(rows)


def output_file(filename):
    """Resolve one URL-decoded output filename without allowing directory traversal."""
    safe_name = Path(filename).name
    if not filename or safe_name != filename or safe_name in (".", ".."):
        abort(400, description="Invalid filename")
    return OUTPUT_DIR / safe_name


@app.get("/api/download/<path:filename>")
def download(filename):
    path = output_file(filename)
    if not path.is_file(): abort(404)
    return send_file(path, as_attachment=request.args.get("inline") != "1", download_name=path.name)


@app.get("/api/preview/<path:filename>")
def preview(filename):
    path = output_file(filename)
    if not path.is_file(): abort(404)
    return send_file(path, as_attachment=False, download_name=path.name)


@app.delete("/api/downloads/<path:filename>")
def delete_download(filename):
    path = output_file(filename)
    if not path.is_file(): return jsonify({"success": False, "message": "File not found."}), 404
    path.unlink(); return jsonify({"success": True, "message": "File deleted."})

@app.delete("/api/downloads")
def clear_downloads():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True); deleted = 0
    for path in OUTPUT_DIR.iterdir():
        if path.is_file(): path.unlink(); deleted += 1
    return jsonify({"success": True, "message": f"Deleted {deleted} files."})

def main():
    print(f"ZVRION LeadFlow running at http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)

if __name__ == "__main__": main()
