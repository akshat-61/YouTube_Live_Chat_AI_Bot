from pymongo import MongoClient
from datetime import datetime

MONGODB_URI = "mongodb://chatsrvs_mongo:chat%40456@10.172.3.7:27017/chat_srvs?authSource=admin"
MONGODB_DATABASE = "chat_srvs"

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
live_sessions = db["live_sessions"]

def generate_session_id():
    return "SESSION_" + datetime.now().strftime("%Y%m%d_%H%M%S")

def insert_live_session(channel_id, video_id, chat_room_id):
    existing = live_sessions.find_one({"video_id": video_id})

    if existing:
        return existing["session_id"]

    session_id = generate_session_id()

    data = {
        "session_id": session_id,
        "channel_id": channel_id,
        "video_id": video_id,
        "chat_room_id": chat_room_id,
        "live_video_link": ...,
        "chat_room_id": ...,
        "status": "active",
        "title": "",
        "viewer_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "ended_at": None
    }

    live_sessions.insert_one(data)
    return session_id

def get_active_sessions():
    return list(live_sessions.find({"status":"active"}))

def get_all_sessions():
    return list(live_sessions.find().sort("_id", -1))

def get_latest_active_session():
    return live_sessions.find_one(
        {"status": "active"},
        sort=[("_id", -1)]
    )

def get_session_by_video_id(video_id):
    return live_sessions.find_one({"video_id": video_id})

def get_session_by_session_id(session_id):
    return live_sessions.find_one({"session_id": session_id})

def update_session_status(session_id, status):
    return live_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"status": status}}
    )

def delete_session(session_id):
    return live_sessions.delete_one({"session_id": session_id})

def clear_all_sessions():
    return live_sessions.delete_many({})

def count_sessions():
    return live_sessions.count_documents({})

def end_session(video_id):
    return live_sessions.update_one(
        {"video_id": video_id},
        {
            "$set": {
                "status": "ended",
                "ended_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )