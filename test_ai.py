from ai_engine import generate_reply, is_relevant_question
import random

context = "Python programming stream covering web scraping, BeautifulSoup, APIs, and debugging"

users = ["Akshat", "Rahul", "Priya", "Aman", "Neha", "Rohit", "Simran", "Dev", "Ankit", "Kiran"]

questions = [
    # 🔹 Installation & Setup
    "How do I install BeautifulSoup?",
    "how to install bs4 in python",
    "pip install bs4 not working why",
    "how to install requests library",
    "how to install selenium",
    "why pip install is failing",
    "how to upgrade pip",
    "how to install python packages offline",
    "how to fix permission denied in pip",
    "how to install libraries in virtualenv",

    # 🔹 Basics
    "What is BeautifulSoup used for?",
    "what is web scraping",
    "what is html parsing",
    "how does bs4 work",
    "what is DOM in web scraping",
    "difference between html and xml",
    "what is a tag in html",
    "how to read html file in python",
    "how to extract data from html",
    "what is parser in bs4",

    # 🔹 Parsing & Extraction
    "how to parse html in python",
    "how to extract links using bs4",
    "how to get all images from a webpage",
    "how to extract text from html",
    "how to find elements by class name",
    "how to use find_all in bs4",
    "how to extract table data",
    "how to scrape headings from webpage",
    "how to extract meta tags",
    "how to scrape nested tags",

    # 🔹 Requests & Networking
    "how to use requests with bs4",
    "how to send headers in requests",
    "why am i getting 403 forbidden",
    "how to use user agent in requests",
    "how to make get request in python",
    "how to handle cookies in requests",
    "how to use proxies in requests",
    "how to retry failed requests",
    "how to increase timeout in requests",
    "how to send post request in python",

    # 🔹 Errors & Debugging
    "why my bs4 code is not working",
    "module not found error bs4",
    "attribute error in bs4",
    "how to debug python scraping code",
    "why find_all returns empty list",
    "how to fix NoneType error",
    "why my scraper returns blank",
    "how to debug html parsing issues",
    "how to check response content",
    "how to print html response",

    # 🔹 Advanced Scraping
    "how to scrape dynamic websites",
    "difference between selenium and bs4",
    "when to use selenium instead of bs4",
    "how to scrape javascript website",
    "how to scroll page using selenium",
    "how to click button using selenium",
    "how to wait for element in selenium",
    "how to handle infinite scroll",
    "how to scrape ajax content",
    "how to handle login in scraping",

    # 🔹 Performance & Scaling
    "how to scrape faster in python",
    "how to use threading in scraping",
    "how to use async in python scraping",
    "how to scrape multiple pages",
    "how to optimize scraping speed",
    "how to avoid blocking while scraping",
    "how to batch requests",
    "how to scrape large websites",
    "how to reduce memory usage in scraping",
    "how to scale scraping system",

    # 🔹 Data Handling
    "how to save scraped data to csv",
    "how to save data to json",
    "how to store scraped data in database",
    "how to clean scraped data",
    "how to remove duplicates from data",
    "how to export data to excel",
    "how to parse data into pandas",
    "how to structure scraped data",
    "how to handle missing data",
    "how to validate scraped data",

    # 🔹 Real-world Use Cases
    "how to scrape amazon product data",
    "how to scrape flipkart products",
    "how to scrape job listings",
    "how to scrape news websites",
    "how to scrape google search results",
    "how to scrape price data",
    "how to scrape reviews from website",
    "how to scrape social media data",
    "how to scrape images from website",
    "how to scrape ecommerce data",

    # 🔹 Edge Cases & Legal
    "is web scraping legal",
    "how to avoid getting blocked",
    "how to bypass captcha",
    "how to rotate proxies",
    "how to use vpn for scraping",
    "how to respect robots.txt",
    "how to avoid ip ban",
    "how to detect scraping blocks",
    "how to handle rate limiting",
    "how to scrape safely",

    # 🔹 Mixed / Natural Language
    "my code is not working can you help",
    "i am getting error in bs4 installation",
    "can you explain scraping simply",
    "how do i start web scraping",
    "which library is best for scraping",
    "what should i learn for scraping",
    "how to become good at web scraping",
    "why scraping is useful",
    "can i use python for scraping",
    "is bs4 enough for scraping",
]

# ❌ Noise / spam / useless messages
noise = [
    "nice", "lol", "🔥🔥🔥", "brooo", "hello", "hi",
    "😂😂😂", "good stream", "love you bro",
    "first comment", "op", "wow", "amazing"
]

variations = [
    "how to install beautiful soup",
    "how do i install bs4",
    "install bs4 python",
    "bs4 install kaise kare",
    "how to setup beautifulsoup",
    "steps to install bs4",
    "pip install beautifulsoup4 kaise kare",
    "bs4 kaise install kare python me",
    "how can i install bs4",
    "install beautiful soup library"
]

# 🔥 Generate large mixed chat
messages = []

for i in range(200):  # 👈 Increase to 500+ for heavy testing
    user = random.choice(users)

    msg_type = random.choice(["question", "noise", "variation"])

    if msg_type == "question":
        text = random.choice(questions)
    elif msg_type == "variation":
        text = random.choice(variations)
    else:
        text = random.choice(noise)

    messages.append({"user": user, "message": text})


print("🚀 MASSIVE CHAT SIMULATION STARTED...\n")

for msg in messages:
    user = msg["user"]
    text = msg["message"]

    print(f"💬 {user}: {text}")

    if not is_relevant_question(text, context):
        print("⛔ Skipped\n")
        continue

    reply = generate_reply(text, user, context)

    if reply:
        print(f"🤖 Reply: {reply}\n")
    else:
        print("⚠️ No reply\n")