import os
from pathlib import Path
from dotenv import load_dotenv
import json

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

    # Mail of bot
    EMAIL_LOGIN = os.getenv("BOT_EMAIL_LOGIN")
    EMAIL_PASSWORD = os.getenv("BOT_EMAIL_PASSWORD")
    IMAP_SERVER = "imap.yandex.ru"

    PROVERKACHEKA_TOKEN = os.getenv("PROVERKACHEKA_TOKEN")

    # Google
    _creds_relative_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "creds/service_account.json")
    GOOGLE_CREDS_PATH = str(BASE_DIR / _creds_relative_path)

    with open(GOOGLE_CREDS_PATH, "r", encoding="utf-8") as f:
        GOOGLE_SERVICE_EMAIL = json.load(f).get("client_email", "SERVICE_EMAIL_NOT_FOUND")

    WHITELIST_PATH = BASE_DIR / "data/whitelist.txt"

    @classmethod
    def validate(cls):
        required = {
            "TELEGRAM_TOKEN": cls.BOT_TOKEN,
            "BOT_EMAIL_LOGIN": cls.EMAIL_LOGIN,
            "BOT_EMAIL_PASSWORD": cls.EMAIL_PASSWORD
        }
        missing = [key for key, val in required.items() if not val]

        if missing:
            error_msg = f"Missing required environment variables: {', '.join(missing)}"
            raise ValueError(error_msg)

    @classmethod
    def get_whitelisted_users(cls) -> list[str]:
        if not cls.WHITELIST_PATH.exists():
            return []
        with open(cls.WHITELIST_PATH, "r", encoding="utf-8") as f:
            return [line.strip().lstrip('@').lower() for line in f if line.strip()]

config = Config()