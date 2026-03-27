import gspread
from app.core.logger import logger
from app.exporters.tabs.receipts_tab import ReceiptsTab

class UserSpreadsheet:
    def __init__(self, client: gspread.Client, spreadsheet_id: str = None):
        self.client = client
        self.spreadsheet_id = spreadsheet_id
        self.document: gspread.Spreadsheet = None

        if self.spreadsheet_id:
            self._open_existing()

    def _open_existing(self):
        try:
            self.document = self.client.open_by_key(self.spreadsheet_id)
        except Exception as e:
            logger.error(f"Failed to open spreadsheet {self.spreadsheet_id}: {e}")
            raise

    def get_receipts_tab(self) -> ReceiptsTab:
        try:
            ws = self.document.worksheet("Чеки")
        except gspread.WorksheetNotFound:
            logger.info("'Receipts' tab not found. Creating a new one...")
            ws = self.document.add_worksheet(title="Чеки", rows=1000, cols=10)
        tab = ReceiptsTab(ws)
        tab.setup_headers()
        return tab

    def get_analytics_tab(self):
        # TODO
        try:
            ws = self.document.worksheet("Аналитика")
        except gspread.WorksheetNotFound:
            ws = self.document.add_worksheet(title="Аналитика", rows=100, cols=20)
        # return AnalyticsTab(ws)
        return ws