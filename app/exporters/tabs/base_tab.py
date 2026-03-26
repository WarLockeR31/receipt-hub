import gspread
from app.core.logger import logger
from gspread.utils import a1_range_to_grid_range

class BaseTab:
    def __init__(self, worksheet: gspread.Worksheet):
        self.ws = worksheet

    def _get_grid_range(self, range_a1: str) -> dict:
        grid_range = a1_range_to_grid_range(range_a1, sheet_id=self.ws.id)
        return grid_range

    def apply_batch_update(self, requests: list):
        body = {"requests": requests}
        try:
            self.ws.spreadsheet.batch_update(body)
        except Exception as e:
            logger.error(f"batch_update error on sheet {self.ws.title}: {e}")
            raise