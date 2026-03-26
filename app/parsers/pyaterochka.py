import re
from datetime import datetime
from bs4 import BeautifulSoup
from app.parsers.base_parser import BaseReceiptParser
from app.core.logger import logger


from app.models.receipt import Receipt, ReceiptItem, StoreType, Unit


class BeelinePyaterochkaParser(BaseReceiptParser):
    @classmethod
    def is_applicable(cls, html_content: str, soup: BeautifulSoup) -> bool:
        is_beeline = "ofdreceipt@beeline.ru" in html_content or "ofd.beeline.ru" in html_content
        is_agrotorg = "Агроторг" in html_content or "Пятерочка" in html_content
        return is_beeline and is_agrotorg

    def parse(self):
        logger.info("Starting parsing using BeelinePyaterochkaParser")

        # Date Time
        receipt_datetime = datetime.now()
        dt_td = self.soup.find(lambda tag: tag.name == 'td' and 'Дата | Время' == tag.text)

        if dt_td:
            next_td = dt_td.find_next('td')
            if next_td:
                dt_str = next_td.text.strip()
                try:
                    receipt_datetime = datetime.strptime(dt_str, "%d.%m.%Y | %H:%M")
                except ValueError:
                    logger.error(f"Could not parse date from string: {dt_str}")

        # Total sum
        total_sum = 0.0
        total_td = self.soup.find(lambda tag: tag.name == 'td' and 'Итог' == tag.text)

        if total_td:
            next_td = total_td.find_next('td')
            if next_td:
                try:
                    total_sum = float(next_td.text.strip())
                except ValueError:
                    logger.error("Could not parse total sum")

        # Items
        items = []
        index_tds = self.soup.find_all(lambda tag: tag.name == 'td' and re.match(r'^\d+\.$', tag.text.strip()))

        for idx_td in index_tds:
            name_td = idx_td.find_next('td')
            if not name_td:
                continue
            item_name = name_td.text.strip()

            price_label_td = name_td.find_next(lambda tag: tag.name == 'td' and 'Цена * Кол' == tag.text)

            if price_label_td:
                price_val_td = price_label_td.find_next('td')
                if price_val_td:
                    val_text = price_val_td.text.strip()

                    match = re.search(r'([\d\.]+)\s*\*\s*([\d\.]+).*?=\s*([\d\.]+)', val_text)

                    if match:
                        items.append({
                            "name": item_name,
                            "price": float(match.group(1)),
                            "quantity": float(match.group(2)),
                            "sum": float(match.group(3))
                        })

        logger.info(f"Successfully parsed {len(items)} items. Total sum: {total_sum}")

        receipt_items = []
        for it in items:
            receipt_items.append(ReceiptItem(
                name=it["name"],
                price=it["price"],
                quantity=it["quantity"],
                sum=it["sum"],
                unit=Unit.PC
            ))

        receipt_id = f"receipt_{int(receipt_datetime.timestamp())}"

        return Receipt(
            id=receipt_id,
            datetime=receipt_datetime,
            store=StoreType.PYATEROCHKA,
            total_sum=total_sum,
            items=receipt_items,
            raw_data=self.html_content
        )