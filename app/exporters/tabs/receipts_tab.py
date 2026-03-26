import re
from app.exporters.tabs.base_tab import BaseTab
from app.models.receipt import Receipt
from app.core.logger import logger

class ReceiptsTab(BaseTab):
    def setup_headers(self):
        if not self.ws.acell('A1').value:
            headers = ["Дата", "Магазин / Товар", "Кол-во", "Ед. изм.", "Цена за ед.", "Сумма"]
            self.ws.append_row(headers)

            self.ws.freeze(rows=1)
            self.ws.format("A1:F1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            })
            logger.info("Headers for 'Receipts' tab successfully created.")

            body = {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": self.ws.id,
                                "gridProperties": {
                                    "rowGroupControlAfter": False
                                }
                            },
                            "fields": "gridProperties.rowGroupControlAfter"
                        }
                    }
                ]
            }
            self.ws.spreadsheet.batch_update(body)
            logger.info("Group display configured: button on top.")

    def append_nested_receipt(self, receipt: Receipt):
        rows_to_insert = []

        date_str = receipt.datetime.strftime("%Y-%m-%d %H:%M")

        header_row = [
            f"▼ {date_str}",
            f"🛒 {receipt.store.value} (Чек #{receipt.id[-5:]})",
            "",
            "",
            "ИТОГО:",
            receipt.total_sum
        ]
        rows_to_insert.append(header_row)

        # Nested rows
        for item in receipt.items:
            item_row = [
                "",
                f"   ↳ {item.name}",
                item.quantity,
                item.unit.value,
                item.price,
                item.sum
            ]
            rows_to_insert.append(item_row)

        response = self.ws.append_rows(rows_to_insert)

        updated_range = response.get('updates', {}).get('updatedRange', '')
        logger.info(f"Google confirmed insertion in range: {updated_range}")

        match = re.search(r'A(\+?\d+)', updated_range)
        if not match:
            logger.error("Failed to determine row index from Google response")
            return

        start_index = int(match.group(1))
        end_index = start_index + len(receipt.items)

        header_range = f"A{start_index}:F{start_index}"
        header_union_range = f"B{start_index}:D{start_index}"
        items_range = f"A{start_index + 1}:F{start_index + len(receipt.items)}"

        group_request = [
            {
                "addDimensionGroup": {
                    "range": {
                        "sheetId": self.ws.id,
                        "dimension": "ROWS",
                        "startIndex": start_index,
                        "endIndex": end_index
                    }
                }
            },
            {
                "mergeCells": {
                    "range": self._get_grid_range(header_union_range),
                    "mergeType": "MERGE_ALL"
                }
            }
        ]

        format_requests = [
            {
                "range": header_range,
                "format": {
                    "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 1.0},
                    "textFormat": {"bold": True},
                    # "borders": {
                    #     "bottom": {"style": "SOLID_MEDIUM", "color": {"red": 0.4, "green": 0.4, "blue": 0.4}}
                    # }
                }
            },
            {
                "range": items_range,
                "format": {
                    "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                     "textFormat": {"italic": True}
                }
            }
        ]

        self.apply_batch_update(group_request)
        self.ws.batch_format(format_requests)
        logger.info(f"Receipt {receipt.id} exported to Google Sheet with collapsed items.")