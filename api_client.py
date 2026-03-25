import requests
import uuid

API_URL = "https://dev-apigateway.extramarks.com/ai-chat/chat"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_TOKEN"
}


def get_reply(message: str) -> str:
    data = {
        "sender_uuid": str(uuid.uuid4()),
        "chat_room_id": 240,
        "message": message,
        "board_id": 180,
        "class_id": 1581786,
        "subject_id": 4900778,
        "query_ppt_slide": None,
        "query_image_path": None,
        "query_content_path": None,
        "message_id": str(uuid.uuid4())
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=data)

        if response.status_code == 200:
            return response.text
        else:
            print(f"[API ERROR] {response.status_code}: {response.text}")
            return ""

    except Exception as e:
        print(f"[API EXCEPTION] {e}")
        return ""