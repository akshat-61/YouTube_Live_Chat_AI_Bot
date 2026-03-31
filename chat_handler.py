import json
import os
import time
import threading
import queue
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import logger
from token_manager import ensure_token_fresh
from ai_engine import generate_reply
from context_manager import get_stream_context
from config import (
    POLL_INTERVAL_SECONDS,
    USER_COOLDOWN_SECONDS,
    SEEN_MSGS_FILE,
    CHANNEL_ID,
    TOKEN_FILE,
    MAX_STREAMS,
    STREAM_DISCOVERY_INTERVAL,
    SEEN_MSGS_FLUSH_INTERVAL,
)

_seen_msgs = {}
_seen_msgs_lock = threading.Lock()

_user_cooldowns = {}
_cooldowns_lock = threading.Lock()

_active_threads = {}
_threads_lock = threading.Lock()

_stream_context_cache = {}
_context_lock = threading.Lock()

# ── NEW: lock to protect token.json from concurrent refresh ──────────────────
_token_lock = threading.Lock()

message_queue = queue.Queue()


def _get_youtube_client():
    """
    Always create a fresh YouTube client.
    Token refresh is serialised with _token_lock so multiple threads
    cannot corrupt token.json simultaneously.
    """
    with _token_lock:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
    # Build outside the lock — network I/O, no shared state
    return build("youtube", "v3", credentials=creds)


def _mark_seen(video_id, msg_id):
    with _seen_msgs_lock:
        if video_id not in _seen_msgs:
            _seen_msgs[video_id] = set()
        if msg_id in _seen_msgs[video_id]:
            return False
        _seen_msgs[video_id].add(msg_id)
        return True


def _get_stream_context(video_id):
    with _context_lock:
        if video_id in _stream_context_cache:
            return _stream_context_cache[video_id]
    ctx = get_stream_context(video_id)
    with _context_lock:
        _stream_context_cache[video_id] = ctx
    return ctx


def _fetch_messages_worker(video_id):
    yt = _get_youtube_client()
    res = yt.videos().list(part="liveStreamingDetails", id=video_id).execute()
    items = res.get("items", [])
    if not items:
        return

    chat_id = items[0]["liveStreamingDetails"].get("activeLiveChatId")
    if not chat_id:
        return

    ctx = _get_stream_context(video_id)["combined"]

    while True:
        try:
            res = yt.liveChatMessages().list(
                liveChatId=chat_id,
                part="snippet,authorDetails",
            ).execute()

            for msg in res.get("items", []):
                msg_id = msg["id"]
                if not _mark_seen(video_id, msg_id):
                    continue

                message_queue.put((video_id, chat_id, msg, ctx))

            time.sleep(2)

        except Exception:
            time.sleep(5)


def _process_messages_worker():
    """
    Each iteration builds a FRESH yt client only when it needs to send a reply.
    This avoids any shared credentials state between threads.
    """
    while True:
        try:
            video_id, chat_id, msg, ctx = message_queue.get()
            print(f"[QUEUE] {video_id} | {msg['authorDetails']['displayName']} → {msg['snippet']['displayMessage']}", flush=True)
            print(f"[QUEUE SIZE] {message_queue.qsize()}", flush=True)

            username = msg["authorDetails"]["displayName"]
            text = msg["snippet"]["displayMessage"]

            now = time.time()

            with _cooldowns_lock:
                if video_id not in _user_cooldowns:
                    _user_cooldowns[video_id] = {}
                last = _user_cooldowns[video_id].get(username, 0)

            if now - last < USER_COOLDOWN_SECONDS:
                print(f"[SKIP] {video_id} | {username} → {text}", flush=True)
                continue

            if len(text.split()) < 2:
                print(f"[SKIP][TOO_SHORT] {video_id} | {username} → {text}", flush=True)
                continue

            if text.startswith("@"):
                print(f"[SKIP][BOT_REPLY] {video_id} | {username} → {text}", flush=True)
                continue

            start = time.time()
            reply = generate_reply(text, username, ctx)
            latency = time.time() - start

            if latency > 8:
                print(f"[SLOW] {latency:.2f}s | {video_id} | {username}", flush=True)

            if not reply:
                reply = f"{username} please wait, answering shortly!"

            tag = username if username.startswith("@") else f"@{username}"
            final = reply if reply.startswith(tag) else f"{tag} {reply}"

            # ── FIX: trim AFTER prepending tag — tag itself adds ~15 chars ───
            # ai_engine trims to 200 but tag prepend can push it to 215+
            # YouTube hard limit is 200 chars → causes INVALID_REQUEST_METADATA
            if len(final) > 200:
                cut = final[:200]
                last_dot = cut.rfind(".")
                final = cut[:last_dot + 1] if last_dot > 50 else cut[:197] + "..."

            # ── FIX: fresh client per reply — no shared credentials state ────
            try:
                yt = _get_youtube_client()
                yt.liveChatMessages().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "liveChatId": chat_id,
                            "type": "textMessageEvent",
                            "textMessageDetails": {"messageText": final},
                        }
                    },
                ).execute()
                print(f"[REPLY] {video_id} | {username} → {final}", flush=True)

                with _cooldowns_lock:
                    _user_cooldowns[video_id][username] = now

            except Exception as e:
                print(f"[ERROR] {e}", flush=True)
                logger.log_error("reply_send", str(e))

        except Exception:
            time.sleep(2)


def _spawn_stream(video_id):
    with _threads_lock:
        if video_id in _active_threads:
            return

        t = threading.Thread(target=_fetch_messages_worker, args=(video_id,), daemon=True)
        _active_threads[video_id] = t
        t.start()


def run():
    for _ in range(3):
        threading.Thread(target=_process_messages_worker, daemon=True).start()

    while True:
        try:
            yt = _get_youtube_client()
            res = yt.search().list(
                part="id",
                channelId=CHANNEL_ID,
                eventType="live",
                type="video",
                maxResults=MAX_STREAMS,
            ).execute()

            vids = [i["id"]["videoId"] for i in res.get("items", [])]

            for v in vids:
                _spawn_stream(v)

            time.sleep(STREAM_DISCOVERY_INTERVAL)

        except Exception:
            time.sleep(10)