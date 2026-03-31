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

_token_lock = threading.Lock()

message_queue = queue.Queue()

_YT_CHAR_LIMIT = 200

_MULTI_PART_DELAY = 1.5


def _get_youtube_client():
    with _token_lock:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
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


def _split_reply(tag: str, reply: str) -> list[str]:
    import re

    clean_reply = reply
    if reply.startswith(tag):
        clean_reply = reply[len(tag):].lstrip()

    if len(f"{tag} {clean_reply}") <= _YT_CHAR_LIMIT:
        return [f"{tag} {clean_reply}"]

    sentences = re.split(r'(?<=[.?!])\s+', clean_reply.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    LABEL_RESERVE = 8
    available = _YT_CHAR_LIMIT - len(tag) - 1 - LABEL_RESERVE

    raw_parts = []
    current = ""

    for sentence in sentences:
        if len(sentence) > available:
            if current:
                raw_parts.append(current)
                current = ""
            words = sentence.split()
            chunk = ""
            for word in words:
                candidate = f"{chunk} {word}".strip()
                if len(candidate) <= available:
                    chunk = candidate
                else:
                    if chunk:
                        raw_parts.append(chunk)
                    chunk = word
            if chunk:
                raw_parts.append(chunk)
        else:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= available:
                current = candidate
            else:
                if current:
                    raw_parts.append(current)
                current = sentence

    if current:
        raw_parts.append(current)

    total = len(raw_parts)
    result = []
    for i, part in enumerate(raw_parts, 1):
        label = f" ({i}/{total})" if total > 1 else ""
        msg = f"{tag} {part}{label}"
        if len(msg) > _YT_CHAR_LIMIT:
            overhead = len(tag) + 1 + len(label)
            msg = f"{tag} {part[:_YT_CHAR_LIMIT - overhead - 3]}...{label}"
        result.append(msg)

    return result


def _send_message(yt, chat_id: str, text: str):
    yt.liveChatMessages().insert(
        part="snippet",
        body={
            "snippet": {
                "liveChatId": chat_id,
                "type": "textMessageEvent",
                "textMessageDetails": {"messageText": text},
            }
        },
    ).execute()


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
                reply = f"please wait, answering shortly!"

            tag = username if username.startswith("@") else f"@{username}"

            # Split into multiple parts if needed — nothing gets cut
            parts = _split_reply(tag, reply)

            try:
                yt = _get_youtube_client()

                for i, part in enumerate(parts):
                    _send_message(yt, chat_id, part)
                    print(f"[REPLY {i+1}/{len(parts)}] {video_id} | {username} → {part}", flush=True)

                    # Delay between parts to avoid rate limiting
                    if i < len(parts) - 1:
                        time.sleep(_MULTI_PART_DELAY)

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