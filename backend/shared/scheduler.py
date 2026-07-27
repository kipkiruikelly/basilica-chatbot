import threading
import time
import os
import json
from backend.infrastructure.logging import log_event

CONTENT_FILE = "admin_content.json"
VERSIONS_FILE = "admin_versions.json"

def load_json(filepath, default_val):
    if not os.path.exists(filepath):
        return default_val
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception:
        return default_val

def save_json(filepath, data):
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_event("scheduler_save_error", {"file": filepath, "error": str(e)}, "error")

def run_scheduler_tick():
    items = load_json(CONTENT_FILE, [])
    versions = load_json(VERSIONS_FILE, [])
    now = time.time()
    changed = False

    for item in items:
        # 1. Scheduled Publication checks
        if item.get("status") == "Scheduled" and item.get("scheduled_for"):
            if now >= item["scheduled_for"]:
                item["status"] = "Published"
                item["published_at"] = now
                item["published_by"] = "System Scheduler"
                item["version"] += 1
                item["updated_at"] = now
                item["change_notes"] = "Automatically published by Scheduler"
                
                # Append Version history state
                versions.append({
                    "content_id": item["id"],
                    "version": item["version"],
                    "title": item["title"],
                    "content_data": item["content_data"],
                    "status": "Published",
                    "updated_by": "System Scheduler",
                    "updated_at": now,
                    "change_notes": item["change_notes"]
                })
                changed = True
                log_event("scheduler_auto_publish", {"id": item["id"], "title": item["title"]})

        # 2. Expiration Archiving checks
        elif item.get("status") == "Published" and item.get("expiry_date"):
            if now >= item["expiry_date"]:
                item["status"] = "Archived"
                item["version"] += 1
                item["updated_at"] = now
                item["change_notes"] = "Automatically archived by Scheduler (Expired)"
                
                # Append Version history state
                versions.append({
                    "content_id": item["id"],
                    "version": item["version"],
                    "title": item["title"],
                    "content_data": item["content_data"],
                    "status": "Archived",
                    "updated_by": "System Scheduler",
                    "updated_at": now,
                    "change_notes": item["change_notes"]
                })
                changed = True
                log_event("scheduler_auto_archive", {"id": item["id"], "title": item["title"]})

    if changed:
        save_json(CONTENT_FILE, items)
        save_json(VERSIONS_FILE, versions)

def _scheduler_worker():
    while True:
        try:
            run_scheduler_tick()
        except Exception as e:
            log_event("scheduler_worker_error", {"error": str(e)}, "error")
        time.sleep(10)

def start_scheduler():
    t = threading.Thread(target=_scheduler_worker, daemon=True)
    t.start()
    log_event("scheduler_started", {"interval_seconds": 10})
