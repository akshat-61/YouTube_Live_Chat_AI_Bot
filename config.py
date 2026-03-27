import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Missing required env var: {key}\n"
            f"Copy .env.example → .env and fill it in."
        )
    return value

YOUTUBE_CLIENT_SECRET_FILE: str = _require("YOUTUBE_CLIENT_SECRET_FILE")
CHANNEL_ID: str                 = _require("CHANNEL_ID")

API_URL: str = _require("API_URL")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
USER_COOLDOWN_SECONDS = int(os.getenv("USER_COOLDOWN_SECONDS", "30"))
SEEN_MSGS_FILE        = os.getenv("SEEN_MSGS_FILE",         "seen_msgs.json")
LOG_FILE              = os.getenv("LOG_FILE",               "chat_log.json")
STREAM_CONTEXT_FILE   = os.getenv("STREAM_CONTEXT_FILE",    "stream_context.txt")