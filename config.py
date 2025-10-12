import os
from dotenv import load_dotenv

# Load .env automatically
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")
CHANEL_ID = os.getenv("CHANEL_ID")
