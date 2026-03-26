from datetime import datetime
from app.models.receipt import Receipt, ReceiptItem, StoreType, Unit
from app.core.logger import logger

class ProverkaChekaParser:
    @staticmethod
    def parse(json_response: dict) -> Receipt:
        if json_response.get('code') != 1:
            logger.error(f"API returned an error or receipt not found: {json_response.get('code')}")
            return None

        data = json_response.get('data', {}).get('json', {})
        if not data:
            return None

        store_name = data.get('user', 'Неизвестный магазин')

        date_str = data.get('ticketDate')
        try:
            receipt_datetime = datetime.fromisoformat(date_str)
        except:
            receipt_datetime = datetime.now()

        total_sum = data.get('totalSum', 0) / 100.0

        receipt_items = []
        for item in data.get('items', []):
            receipt_items.append(ReceiptItem(
                name=item.get('name', 'Товар'),
                price=item.get('price', 0) / 100.0,
                quantity=item.get('quantity', 1),
                sum=item.get('sum', 0) / 100.0,
                unit=Unit.PC
            ))

        fd = data.get('fiscalDocumentNumber', int(receipt_datetime.timestamp()))
        receipt_id = f"receipt_fd_{fd}"

        return Receipt(
            id=receipt_id,
            datetime=receipt_datetime,
            store=StoreType.OTHER,
            total_sum=total_sum,
            items=receipt_items,
            raw_data=str(json_response)
        )