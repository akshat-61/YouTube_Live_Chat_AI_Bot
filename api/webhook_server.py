import xml.etree.ElementTree as ET

from flask import Flask, request
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

import logger
from chat_handler import _spawn_worker
from config import TOKEN_FILE

app = Flask(__name__)


def _get_youtube():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    return build("youtube", "v3", credentials=creds)


def _extract_video_id(xml_data: bytes) -> str | None:
    try:
        root = ET.fromstring(xml_data)
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            vid = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId")
            if vid is not None and vid.text:
                return vid.text
    except ET.ParseError as e:
        logger.log_error("webhook_xml_parse", str(e))
    return None


def _is_live(video_id: str) -> bool:
    try:
        youtube = _get_youtube()
        res = youtube.videos().list(
            part="liveStreamingDetails",
            id=video_id,
        ).execute()
        items = res.get("items", [])
        if not items:
            return False
        return bool(items[0].get("liveStreamingDetails", {}).get("activeLiveChatId"))
    except Exception as e:
        logger.log_error(f"webhook_is_live:{video_id}", str(e))
        return False
7

@app.route("/webhook/youtube", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return request.args.get("hub.challenge", ""), 200

    video_id = _extract_video_id(request.data)
    if not video_id:
        return "", 200

    if _is_live(video_id):
        print(f"[Webhook] Live stream detected: {video_id}")
        logger.log_info("Webhook triggered", video_id=video_id)
        _spawn_worker(video_id)

    return "", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)