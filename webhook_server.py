from flask import Flask, request
import xml.etree.ElementTree as ET
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from chat_handler import start_bot_for_video

ACTIVE_VIDEO = None

app = Flask(__name__)

TOKEN_FILE = "token.json"

def get_youtube():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    return build("youtube", "v3", credentials=creds)

@app.route("/webhook/youtube", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return request.args.get("hub.challenge", "")

    data = request.data
    root = ET.fromstring(data)

    video_id = None
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        vid = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId")
        if vid is not None:
            video_id = vid.text

    if not video_id:
        return "", 200

    youtube = get_youtube()

    res = youtube.videos().list(
        part="liveStreamingDetails",
        id=video_id
    ).execute()

    items = res.get("items", [])
    if not items:
        return "", 200

    chat_id = items[0]["liveStreamingDetails"].get("activeLiveChatId")

    if chat_id:
        print(f"[Webhook] LIVE detected: {video_id}")
        start_bot_for_video(video_id, chat_id)

    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)