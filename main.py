import sys
import config
from chat_handler import run

if __name__ == "__main__":
    try:
        _ = config.CHANNEL_ID
        _ = config.API_URL
        _ = config.YOUTUBE_CLIENT_SECRET_FILE
    except EnvironmentError as e:
        print(f"[Startup Error] {e}")
        sys.exit(1)

    run()