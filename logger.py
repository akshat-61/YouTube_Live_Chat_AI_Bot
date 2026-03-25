import json
from datetime import datetime, timezone
from config import LOG_FILE


def _write(record: dict):
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_replied(video_id: str, username: str, message: str, reply: str):
    _write({
        "event":    "replied",
        "video_id": video_id,
        "user":     username,
        "message":  message,
        "reply":    reply,
    })


def log_skipped(video_id: str, username: str, message: str, reason: str):
    _write({
        "event":    "skipped",
        "video_id": video_id,
        "user":     username,
        "message":  message,
        "reason":   reason,
    })


def log_error(context: str, error: str):
    _write({
        "event":   "error",
        "context": context,
        "error":   error,
    })


def log_info(message: str, **kwargs):
    _write({"event": "info", "message": message, **kwargs})
