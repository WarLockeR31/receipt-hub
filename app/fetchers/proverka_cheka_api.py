import requests
from app.core.config import config
from app.core.logger import logger

class ProverkaChekaAPI:
    def __init__(self):
        self.url = 'https://proverkacheka.com/api/v1/check/get'
        self.token = config.PROVERKACHEKA_TOKEN

    def get_receipt_from_raw(self, qrraw: str) -> dict:
        data = {
            'token': self.token,
            'qrraw': qrraw
        }

        try:
            logger.info(f"Sending qrraw to API: {qrraw}")
            response = requests.post(self.url, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error during API request: {e}")
            return {}