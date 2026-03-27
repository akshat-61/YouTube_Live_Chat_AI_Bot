import requests
import uuid
from config import API_URL, API_TOKEN

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

def get_reply(message: str) -> str:
    data = {
        "sender_uuid": str(uuid.uuid4()),
        "chat_room_id": 240,
        "message": message,
        "board_id": 180,
        "class_id": 1581786,
        "subject_id": 4900778,
        "message_id": str(uuid.uuid4())
    }

    try:
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json=data,
            timeout=5
        )

        response.raise_for_status()
        res_json = response.json()

        return res_json.get("reply", "")

    except requests.exceptions.Timeout:
        print("[API TIMEOUT]")
        return ""

    except requests.exceptions.RequestException as e:
        print(f"[API ERROR] {e}")
        return ""