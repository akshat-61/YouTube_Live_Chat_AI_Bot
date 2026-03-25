import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from config import STREAM_CONTEXT_FILE

TOKEN_FILE = "token.json"


def _get_youtube_client():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    return build("youtube", "v3", credentials=creds)


def get_stream_context(video_id: str) -> dict:
    
    youtube = _get_youtube_client()

    response = youtube.videos().list(
        part="snippet",
        id=video_id
    ).execute()

    items = response.get("items", [])
    if not items:
        return _empty_context()

    snippet = items[0]["snippet"]
    title       = snippet.get("title", "")
    description = snippet.get("description", "")

    custom_context = _load_custom_context()

    combined = _build_combined_context(title, description, custom_context)

    return {
        "title":          title,
        "description":    description,
        "custom_context": custom_context,
        "combined":       combined,
    }


def _load_custom_context() -> str:
    if not os.path.exists(STREAM_CONTEXT_FILE):
        return ""
    with open(STREAM_CONTEXT_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def _build_combined_context(title: str, description: str, custom: str) -> str:
    parts = []
    if title:
        parts.append(f"Stream title: {title}")
    if description:
        desc = description[:1500]
        if len(description) > 1500:
            desc += "... [trimmed]"
        parts.append(f"Stream description:\n{desc}")
    if custom:
        parts.append(f"Additional context from streamer:\n{custom}")
    return "\n\n".join(parts) if parts else "No stream context available."


def _empty_context() -> dict:
    return {
        "title":          "",
        "description":    "",
        "custom_context": "",
        "combined":       "No stream context available.",
    }
