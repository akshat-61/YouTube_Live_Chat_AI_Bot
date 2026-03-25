from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

TOKEN_FILE = "token.json"
USERNAME   = "techscopeindia"


def main():
    creds   = Credentials.from_authorized_user_file(TOKEN_FILE)
    youtube = build("youtube", "v3", credentials=creds)

    response = youtube.search().list(
        part="snippet",
        q=USERNAME,
        type="channel",
        maxResults=1,
    ).execute()

    items = response.get("items", [])
    if not items:
        print(f"No channel found for username: {USERNAME}")
        return

    channel_id = items[0]["snippet"]["channelId"]
    print(f"CHANNEL_ID = {channel_id}")
    print(f"Add this to your .env file as: CHANNEL_ID={channel_id}")


if __name__ == "__main__":
    main()
