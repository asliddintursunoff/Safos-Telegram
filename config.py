import os
from dotenv import load_dotenv

# Load .env automatically
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = (os.getenv("API_URL") or "").rstrip("/")
CHANEL_ID = os.getenv("CHANEL_ID")
# optional: must match API_KEY of the backend when it is set there
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")
