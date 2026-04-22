import re
import uuid
import threading
from collections import OrderedDict

import requests

import logger
from config import API_URL
from em_token_manager import get_fresh_token

_cache: OrderedDict[str, str] = OrderedDict()
_cache_lock                   = threading.Lock()
_CACHE_MAX                    = 300

_context_keyword_cache: dict[str, list[str]] = {}
_context_kw_lock                             = threading.Lock()

BASE_QUESTION_WORDS = {
    "how", "what", "why", "when", "which", "where", "who", "explain",
    "tell me", "can you", "difference", "define", "meaning", "use of",
    "error", "issue", "problem", "help", "understand", "example",
    "#DOUBT", "#Doubt", "Question", "?",
}

IGNORE_EXACT = {
    "lol", "nice", "bro", "hi", "hello", "hlo", "hey", "ok", "okay",
    "😂", "🔥", "👍", "❤️", "wow", "op", "great", "good", "yes", "no",
    "first", "amazing", "cool", "thanks", "thank you", "ty",
}

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "is", "are", "was", "be", "this", "that",
    "it", "its", "by", "from", "as", "we", "will", "about", "our",
    "stream", "title", "description", "context", "course", "series",
}

_API_TIMEOUT = 15


def _cache_get(key: str) -> str | None:
    with _cache_lock:
        if key not in _cache:
            return None
        _cache.move_to_end(key)
        return _cache[key]


def _cache_set(key: str, value: str):
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
        _cache[key] = value
        if len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


def clean_html(text: str) -> str:
    text = re.sub(r'<.*?>', ' ', text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;",   "<")
    text = text.replace("&gt;",   ">")
    text = text.replace("&amp;",  "&")
    text = text.replace("&quot;", '"')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def trim_for_chat(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    cut      = text[:limit]
    last_dot = cut.rfind('.')
    if last_dot > 100:
        return cut[:last_dot + 1]
    return cut[:197] + "..."


def _get_context_keywords(stream_context: str) -> list[str]:
    with _context_kw_lock:
        if stream_context in _context_keyword_cache:
            return _context_keyword_cache[stream_context]

    words    = re.findall(r'\b[a-z]{4,}\b', stream_context.lower())
    keywords = list({w for w in words if w not in _STOP_WORDS})

    with _context_kw_lock:
        _context_keyword_cache[stream_context] = keywords

    return keywords


def is_relevant_question(message: str, stream_context: str) -> bool:
    msg = message.lower().strip()

    if len(msg) < 5:
        return False

    if msg in IGNORE_EXACT:
        return False

    if "http" in msg or "www" in msg:
        return False

    score = 0

    if any(w in msg for w in BASE_QUESTION_WORDS):
        score += 2

    if any(w in msg for w in _get_context_keywords(stream_context)):
        score += 2

    if "?" in msg:
        score += 2

    if len(msg.split()) > 5:
        score += 1

    return score >= 2


def _fallback_reply(username: str) -> str:
    tag = username if username.startswith("@") else f"@{username}"
    return f"{tag} Nice question! Keep watching — we'll cover this soon."


def _build_prompt(message: str, stream_context: str) -> str:
    return (
        "You are a helpful AI assistant in a live YouTube stream.\n\n"
        "Rules:\n"
        "- Answer only questions relevant to the stream topic\n"
        "- Be short and clear — 1 to 2 lines max\n"
        "- Never use bullet points or markdown\n"
        "- If unsure, give a helpful general answer related to the topic\n\n"
        f"Stream Context:\n{stream_context}\n\n"
        f"User Question:\n{message}\n\n"
        "Answer:"
    )


def generate_reply(message: str, username: str, stream_context: str) -> str:
    cleaned = re.sub(r'[^a-z0-9 ]', '', message.lower()).strip()

    cached = _cache_get(cleaned)
    if cached:
        return cached

    try:
        token = get_fresh_token()
    except Exception as e:
        print(f"[ai_engine] Token fetch failed: {e}")
        logger.log_error("ai_engine_token", str(e))
        return _fallback_reply(username)

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "sender_uuid":  str(uuid.uuid4()),
        "chat_room_id": 240,
        "message":      _build_prompt(cleaned, stream_context),
        "board_id":     180,
        "class_id":     1581786,
        "subject_id":   4900778,
        "message_id":   str(uuid.uuid4()),
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=_API_TIMEOUT)

        reply = ""

        if response.status_code == 200:
            json_data = response.json()
            raw = (
                json_data.get("ai_response")
                or json_data.get("response")
                or json_data.get("reply")
                or ""
            )
            reply = clean_html(raw).strip()

        if not reply:
            return _fallback_reply(username)

        reply = trim_for_chat(reply, limit=800)
        _cache_set(cleaned, reply)
        return reply

    except requests.exceptions.Timeout:
        print(f"[ai_engine] Request timed out for: {cleaned[:50]}")
        logger.log_error("ai_engine_timeout", cleaned[:50])
        return _fallback_reply(username)

    except Exception as e:
        print(f"[ai_engine] Unexpected error: {e}")
        logger.log_error("ai_engine_error", str(e))
        return _fallback_reply(username)