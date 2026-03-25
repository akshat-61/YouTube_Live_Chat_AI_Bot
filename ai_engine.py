import requests
import uuid
import re
from config import API_URL, API_TOKEN

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
    """Remove all HTML tags and clean up whitespace."""
    text = re.sub(r'<.*?>', ' ', text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def trim_for_chat(text: str, limit: int = 200) -> str:
    """Trim reply to fit YouTube live chat limit (200 chars)."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_dot = cut.rfind('.')
    if last_dot > 100:
        return cut[:last_dot + 1]
    return cut[:197] + "..."


def _extract_context_keywords(stream_context: str) -> list[str]:
    """
    Pull meaningful words from stream_context to use as topic keywords.
    Filters out short/common words.
    """
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

    return has_question_word or has_context_keyword


def fallback_reply(message: str, stream_context: str = "") -> str:
   
    msg = message.lower()

    if "what is ai" in msg or "what is artificial intelligence" in msg:
        return "AI = Artificial Intelligence. It enables machines to simulate human thinking like learning, reasoning & problem solving."

    if "machine learning" in msg:
        return "Machine Learning is a subset of AI where systems learn from data to improve without being explicitly programmed."

    if "deep learning" in msg:
        return "Deep Learning uses neural networks with many layers to learn complex patterns from large data."

    if "neural network" in msg:
        return "Neural networks are computing systems inspired by the human brain, used in image recognition, NLP, and more."

    if "generative ai" in msg or "genai" in msg:
        return "Generative AI creates new content (text, images, code) by learning patterns from training data. Example: ChatGPT."

    if "llm" in msg or "large language model" in msg:
        return "LLMs are AI models trained on massive text data to understand and generate human language. Examples: GPT-4, Gemini."

    if "nlp" in msg or "natural language" in msg:
        return "NLP = Natural Language Processing. It helps computers understand and respond to human language."

    if "why" in msg and ("ai" in msg or "course" in msg):
        return "AI is transforming every industry — healthcare, finance, education. Learning it now gives you a huge career advantage."

    if "use" in msg and "ai" in msg:
        return "AI is used in voice assistants, recommendation systems, medical diagnosis, self-driving cars, fraud detection and much more."

    if "catalyst" in msg:
        return "In AI context, a catalyst accelerates learning or problem solving — like transfer learning speeds up model training."

    if "difference" in msg and ("ai" in msg or "ml" in msg):
        return "AI is the broad concept of smart machines. ML is a method to achieve AI using data. Deep Learning is a type of ML."

    if "how" in msg and "learn" in msg and "ai" in msg:
        return "Start with Python → learn ML basics (sklearn) → then Deep Learning (TensorFlow/PyTorch) → practice on real datasets."

    if "python" in msg:
        return "Python is the most popular language for AI/ML. Libraries like NumPy, Pandas, TensorFlow, PyTorch are all Python-based."

    if "dataset" in msg or "data" in msg:
        return "Good data is the foundation of AI. Use Kaggle, UCI ML Repository, or Google Dataset Search to find datasets."

    if "install" in msg:
        return "Use: pip install numpy pandas scikit-learn tensorflow to get started with AI in Python."

    if "bs4" in msg or "beautifulsoup" in msg:
        return "Install using: pip install beautifulsoup4"

    if "selenium" in msg:
        return "Use WebDriverWait for dynamic elements in Selenium."

    if "scrape" in msg:
        return "Use requests + BeautifulSoup. For JS sites use Selenium."

    return "Great question! This topic will be covered in the course. Stay tuned and keep asking!"


def generate_reply(message: str, username: str, stream_context: str) -> str:
    cleaned = message.lower().strip()

    if cleaned in cache:
        return cache[cleaned]

    if not is_relevant_question(cleaned, stream_context):
        return ""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }

    data = {
        "sender_uuid": str(uuid.uuid4()),
        "chat_room_id": 240,
        "message": cleaned,
        "board_id": 180,
        "class_id": 1581786,
        "subject_id": 4900778,
        "query_ppt_slide": None,
        "query_image_path": None,
        "query_content_path": None,
        "message_id": str(uuid.uuid4())
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=10)

        reply = ""

        if response.status_code == 200:
            json_data = response.json()
            raw = json_data.get("ai_response") or json_data.get("response") or ""
            reply = clean_html(raw).strip()
        else:
            print(f"[AI] API returned status {response.status_code} — using fallback")

        if not reply:
            reply = fallback_reply(cleaned, stream_context)

        reply = trim_for_chat(reply, limit=200)
        cache[cleaned] = reply
        return reply

    except Exception as e:
        print(f"[AI] Exception: {e} — using fallback")
        return trim_for_chat(fallback_reply(cleaned, stream_context))