import gspread
from google.oauth2.service_account import Credentials
from app.core.config import config
from app.core.logger import logger


def get_google_client() -> gspread.Client:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_CREDS_PATH,
            scopes=scopes
        )

        client = gspread.authorize(creds)
        logger.info("Successfully authorized in Google API")
        return client
    except Exception as e:
        logger.error(f"Error authorizing in Google API: {e}")
        raise