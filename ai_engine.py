import requests
import uuid
import re
from config import API_URL
from em_token_manager import get_fresh_token

cache = {}

BASE_QUESTION_WORDS = [
    "how", "what", "why", "when", "which", "where", "who", "explain",
    "tell me", "can you", "difference", "define", "meaning", "use of",
    "error", "issue", "problem", "help", "understand", "example",
]

IGNORE_EXACT = {
    "lol", "nice", "bro", "hi", "hello", "hlo", "hey", "ok", "okay",
    "😂", "🔥", "👍", "❤️", "wow", "op", "great", "good", "yes", "no",
    "first", "amazing", "cool", "thanks", "thank you", "ty",
}


def clean_html(text: str) -> str:
    text = re.sub(r'<.*?>', ' ', text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def trim_for_chat(text: str, limit: int = 200) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_dot = cut.rfind('.')
    if last_dot > 100:
        return cut[:last_dot + 1]
    return cut[:197] + "..."


def _extract_context_keywords(stream_context: str) -> list[str]:
    
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "is", "are", "was", "be", "this", "that",
        "it", "its", "by", "from", "as", "we", "will", "about", "our",
        "stream", "title", "description", "context", "course", "series",
    }
    words = re.findall(r'\b[a-z]{4,}\b', stream_context.lower())
    return list({w for w in words if w not in stop_words})


def is_relevant_question(message: str, stream_context: str) -> bool:
    message = message.lower().strip()

    if len(message) < 5:
        return False

    if message in IGNORE_EXACT:
        return False

    if "http" in message or "www" in message:
        return False

    has_question_word = any(w in message for w in BASE_QUESTION_WORDS)

    context_keywords = _extract_context_keywords(stream_context)
    has_context_keyword = any(w in message for w in context_keywords)

    score = 0

    if has_question_word:
        score += 2

    if has_context_keyword:
        score += 2

    if "?" in message:
        score += 2

    if len(message.split()) > 5:
        score += 1

    return score >= 2


def fallback_reply(message: str, stream_context: str = "", username: str = "") -> str:
    return (
        f"{username}, Nice question! It's related to what we're discussing "
        f"— keep watching, you'll get clarity soon."
    )


def generate_reply(message: str, username: str, stream_context: str) -> str:
    cleaned = message.lower().strip()

    if cleaned in cache:
        return cache[cleaned]

    if not is_relevant_question(cleaned, stream_context):
        return ""

    final_prompt = f"""
You are a helpful AI assistant in a live YouTube stream.

Your job:
- Understand the stream topic from context
- Answer user questions relevant to the stream
- Be short, clear, and helpful (1-2 lines max)
- If unsure, give a general helpful answer related to the topic

Stream Context:
{stream_context}

User Question:
{cleaned}

Answer:
"""

    # ── Always get a fresh token before calling the API ──────────────────────
    try:
        token = get_fresh_token()
    except Exception as e:
        print(f"[ai_engine] Token fetch failed: {e}")
        return fallback_reply(cleaned, stream_context, username)

    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {token}",
    }

    data = {
        "sender_uuid":  str(uuid.uuid4()),
        "chat_room_id": 240,
        "message":      final_prompt,
        "board_id":     180,
        "class_id":     1581786,
        "subject_id":   4900778,
        "message_id":   str(uuid.uuid4()),
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=10)

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
            reply = fallback_reply(cleaned, stream_context, username)

        reply = trim_for_chat(reply, limit=200)

        if len(cache) > 100:
            cache.clear()

        cache[cleaned] = reply
        return reply

    except Exception:
        return fallback_reply(cleaned, stream_context, username)