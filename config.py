import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

DB_PATH = "data/database.db"

class Config:
    BOT_TOKEN = BOT_TOKEN
    ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else None
    DB_PATH = DB_PATH