import json
import os
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import logger
from ai_engine import is_relevant_question, generate_reply
from context_manager import get_stream_context
from config import (
    POLL_INTERVAL_SECONDS,
    USER_COOLDOWN_SECONDS,
    SEEN_MSGS_FILE,
    CHANNEL_ID,
)

TOKEN_FILE = "token.json"

NO_STREAM_WAIT        = 30
CHAT_ID_LOST_WAIT     = 10
MAX_SEARCH_RETRIES    = 3
SEARCH_RETRY_DELAY    = 5
MAX_CHATID_RETRIES    = 5   
CHATID_RETRY_DELAY    = 6   


def _load_seen_msgs() -> set:
    if os.path.exists(SEEN_MSGS_FILE):
        with open(SEEN_MSGS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def _save_seen_msgs(seen: set):
    with open(SEEN_MSGS_FILE, "w") as f:
        json.dump(list(seen), f)


def _get_youtube_client():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError("OAuth token not found. Run python oauth_setup.py first.")
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def _search_live_video_ids(youtube) -> list[str]:
    for attempt in range(1, MAX_SEARCH_RETRIES + 1):
        try:
            response = youtube.search().list(
                part="id",
                channelId=CHANNEL_ID,
                eventType="live",
                type="video",
            ).execute()
            ids = [item["id"]["videoId"] for item in response.get("items", [])]
            if ids:
                return ids
            print(f"[Bot] search() empty (attempt {attempt}/{MAX_SEARCH_RETRIES}), retrying in {SEARCH_RETRY_DELAY}s...")
            time.sleep(SEARCH_RETRY_DELAY)
        except HttpError as e:
            logger.log_error("search_live_video_ids", str(e))
            time.sleep(SEARCH_RETRY_DELAY)
    return []


def get_chat_id_with_retry(youtube, video_id: str) -> str | None:
    for attempt in range(1, MAX_CHATID_RETRIES + 1):
        try:
            response = youtube.videos().list(
                part="liveStreamingDetails",
                id=video_id,
            ).execute()
            items = response.get("items", [])
            if items:
                chat_id = items[0]["liveStreamingDetails"].get("activeLiveChatId")
                if chat_id:
                    return chat_id
            print(f"[Bot] No activeLiveChatId (attempt {attempt}/{MAX_CHATID_RETRIES}), retrying in {CHATID_RETRY_DELAY}s...")
            time.sleep(CHATID_RETRY_DELAY)
        except (HttpError, IndexError, KeyError) as e:
            logger.log_error(f"get_chat_id:{video_id}", str(e))
            time.sleep(CHATID_RETRY_DELAY)
    return None


def get_messages(youtube, chat_id: str) -> tuple[list, int]:
    try:
        response = youtube.liveChatMessages().list(
            liveChatId=chat_id,
            part="snippet,authorDetails",
        ).execute()
        interval_ms = response.get("pollingIntervalMillis", POLL_INTERVAL_SECONDS * 1000)
        return response.get("items", []), interval_ms
    except HttpError as e:
        logger.log_error(f"get_messages:{chat_id}", str(e))
        return [], POLL_INTERVAL_SECONDS * 1000


def send_reply(youtube, chat_id: str, text: str) -> bool:
    try:
        youtube.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {"messageText": text},
                }
            },
        ).execute()
        return True
    except HttpError as e:
        logger.log_error(f"send_reply:{chat_id}", str(e))
        return False


def run():
    seen_msgs: set                        = _load_seen_msgs()
    user_cooldowns: dict[str, float]      = {}
    stream_context_cache: dict[str, dict] = {}

    cached_video_id: str | None = None
    cached_chat_id:  str | None = None

    env_video_id = os.getenv("LIVE_VIDEO_ID", "").strip()
    if env_video_id:
        cached_video_id = env_video_id
        print(f"[Bot] Using LIVE_VIDEO_ID from .env: {cached_video_id}")

    print("[Bot] Starting YouTube Live Chat AI Bot...")
    logger.log_info("Bot started", channel_id=CHANNEL_ID)

    while True:
        try:
            youtube = _get_youtube_client()

            if cached_video_id:
                chat_id = get_chat_id_with_retry(youtube, cached_video_id)
                if chat_id:
                    cached_chat_id = chat_id
                else:
                    print(f"[Bot] Stream {cached_video_id} ended or chat permanently closed.")
                    logger.log_info("Stream ended", video_id=cached_video_id)
                    if env_video_id:
                        print(f"[Bot] Will keep retrying in {NO_STREAM_WAIT}s...")
                        time.sleep(NO_STREAM_WAIT)
                        continue
                    else:
                        cached_video_id = None
                        cached_chat_id  = None

            if not cached_video_id:
                video_ids = _search_live_video_ids(youtube)
                if not video_ids:
                    print(f"[Bot] No live streams found. Retrying in {NO_STREAM_WAIT}s...")
                    time.sleep(NO_STREAM_WAIT)
                    continue

                for vid in video_ids:
                    cid = get_chat_id_with_retry(youtube, vid)
                    if cid:
                        cached_video_id = vid
                        cached_chat_id  = cid
                        print(f"[Bot] Locked onto stream: {cached_video_id}")
                        logger.log_info("Stream locked", video_id=cached_video_id)
                        break

                if not cached_video_id:
                    print(f"[Bot] Video found but no active chat. Retrying in {CHAT_ID_LOST_WAIT}s...")
                    time.sleep(CHAT_ID_LOST_WAIT)
                    continue

            # ── Step 3: Load stream context once ─────────────────────────────
            if cached_video_id not in stream_context_cache:
                ctx = get_stream_context(cached_video_id)
                stream_context_cache[cached_video_id] = ctx
                print(f"[Bot] Stream: {ctx['title']}")
                logger.log_info("Stream context loaded", video_id=cached_video_id, title=ctx["title"])

            stream_ctx = stream_context_cache[cached_video_id]["combined"]

            # ── Step 4: Poll and reply ────────────────────────────────────────
            messages, poll_interval_ms = get_messages(youtube, cached_chat_id)

            for msg in messages:
                msg_id   = msg["id"]
                username = msg["authorDetails"]["displayName"]
                text     = msg["snippet"]["displayMessage"]

                if msg_id in seen_msgs:
                    continue
                seen_msgs.add(msg_id)

                print(f"[Chat] {username}: {text}")

                now = time.time()
                if now - user_cooldowns.get(username, 0) < USER_COOLDOWN_SECONDS:
                    logger.log_skipped(cached_video_id, username, text, "user_cooldown")
                    continue

                if not is_relevant_question(text, stream_ctx):
                    print(f"[Bot] Not relevant — skipping.")
                    logger.log_skipped(cached_video_id, username, text, "not_relevant")
                    continue

                reply = generate_reply(text, username, stream_ctx)
                if not reply:
                    logger.log_skipped(cached_video_id, username, text, "empty_reply")
                    continue

                sent = send_reply(youtube, cached_chat_id, reply)
                if sent:
                    print(f"[Bot] Replied: {reply}")
                    user_cooldowns[username] = now
                    logger.log_replied(cached_video_id, username, text, reply)
                else:
                    logger.log_skipped(cached_video_id, username, text, "send_failed")

            _save_seen_msgs(seen_msgs)

            wait_s = poll_interval_ms / 1000
            print(f"[Bot] Waiting {wait_s:.1f}s...")
            time.sleep(wait_s)

        except Exception as e:
            print(f"[Bot] Unexpected error: {e}")
            logger.log_error("main_loop", str(e))
            time.sleep(10)