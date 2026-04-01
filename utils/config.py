import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Missing required env var: {key}\n"
            f"Copy .env.example → .env and fill it in."
        )
    return value


def _optional_int(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise EnvironmentError(
            f"Env var {key} must be an integer, got: '{raw}'"
        )
    if value <= 0:
        raise EnvironmentError(
            f"Env var {key} must be a positive integer, got: {value}"
        )
    return value


YOUTUBE_CLIENT_SECRET_FILE: str = _require("YOUTUBE_CLIENT_SECRET_FILE")
CHANNEL_ID: str                 = _require("CHANNEL_ID")
API_URL: str                    = _require("API_URL")

POLL_INTERVAL_SECONDS: int     = _optional_int("POLL_INTERVAL_SECONDS", 10)
USER_COOLDOWN_SECONDS: int     = _optional_int("USER_COOLDOWN_SECONDS", 30)
MAX_STREAMS: int               = _optional_int("MAX_STREAMS", 5)
STREAM_DISCOVERY_INTERVAL: int = _optional_int("STREAM_DISCOVERY_INTERVAL", 300)
SEEN_MSGS_FLUSH_INTERVAL: int  = _optional_int("SEEN_MSGS_FLUSH_INTERVAL", 60)

SEEN_MSGS_FILE: str      = os.getenv("SEEN_MSGS_FILE",      "seen_msgs.json")
LOG_FILE: str            = os.getenv("LOG_FILE",            "chat_log.json")
STREAM_CONTEXT_FILE: str = os.getenv("STREAM_CONTEXT_FILE", "stream_context.txt")
TOKEN_FILE: str          = os.getenv("TOKEN_FILE",          "token.json")