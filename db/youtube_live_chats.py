from pymongo import MongoClient
from datetime import datetime

MONGODB_URI = "mongodb://chatsrvs_mongo:chat%40456@10.172.3.7:27017/chat_srvs?authSource=admin"
MONGODB_DATABASE = "chat_srvs"

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]

chat_messages = db["youtube_chat_messages"]


def create_chat_id(video_id, message_id):
    return f"{video_id}_{message_id}"


def insert_youtube_chat(
    session_id,
    channel_id,
    video_id,
    chat_room_id,
    message_id,
    author_name,
    author_channel_id,
    question,
    reply,
    created_at=None
):
    chat_id = create_chat_id(video_id, message_id)

    existing = chat_messages.find_one({"chat_id": chat_id})

    if existing:
        return chat_id

    data = {
        "chat_id": chat_id,
        "session_id": session_id,
        "channel_id": channel_id,
        "video_id": video_id,
        "chat_room_id": chat_room_id,
        "message_id": message_id,
        "author_name": author_name,
        "author_channel_id": author_channel_id,
        "question": question,
        "reply": reply,
        "answer": None,
        "node_sent": False,
        "node_received": False,
        "status": "question_received",
        "created_at": created_at or datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    chat_messages.insert_one(data)
    return chat_id


def get_unsent_questions():
    return list(
        chat_messages.find(
            {"node_sent": False}
        ).sort("_id", 1)
    )


def mark_sent_to_node(chat_id):
    return chat_messages.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "node_sent": True,
                "status": "sent_to_node",
                "updated_at": datetime.utcnow()
            }
        }
    )


def update_answer_from_node(question, answer):
    return chat_messages.update_one(
        {
            "question": question,
            "node_received": False
        },
        {
            "$set": {
                "answer": answer,
                "node_received": True,
                "status": "answered",
                "updated_at": datetime.utcnow()
            }
        }
    )


def update_answer_by_chat_id(chat_id, answer):
    return chat_messages.update_one(
        {"chat_id": chat_id},
        {
            "$set": {
                "answer": answer,
                "node_received": True,
                "status": "answered",
                "updated_at": datetime.utcnow()
            }
        }
    )


def get_chat_by_id(chat_id):
    return chat_messages.find_one({"chat_id": chat_id})


def get_question_answer(question):
    return chat_messages.find_one({"question": question})


def get_session_chats(session_id):
    return list(
        chat_messages.find(
            {"session_id": session_id}
        ).sort("_id", -1)
    )


def get_video_chats(video_id):
    return list(
        chat_messages.find(
            {"video_id": video_id}
        ).sort("_id", -1)
    )


def get_answered_chats():
    return list(
        chat_messages.find(
            {"status": "answered"}
        ).sort("_id", -1)
    )


def count_total_chats():
    return chat_messages.count_documents({})


def count_answered_chats():
    return chat_messages.count_documents(
        {"status": "answered"}
    )


def clear_chat_collection():
    return chat_messages.delete_many({})