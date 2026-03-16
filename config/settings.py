import os
from dotenv import load_dotenv

load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_TRUNK_ID = os.getenv("LIVEKIT_TRUNK_ID")

PHONE_NUMBER = os.getenv("PHONE_NUMBER")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
