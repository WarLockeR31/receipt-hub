from bs4 import BeautifulSoup
from app.core.logger import logger
from app.parsers.base_parser import BaseReceiptParser
from app.parsers.pyaterochka import BeelinePyaterochkaParser


class ReceiptParserDispatcher:
    def __init__(self):
        self.parsers = [
            BeelinePyaterochkaParser
        ]

    def parse_html(self, html_content: str):
        soup = BeautifulSoup(html_content, 'lxml')

        for parser_class in self.parsers:
            if parser_class.is_applicable(html_content, soup):
                logger.info(f"Matched parser: {parser_class.__name__}")
                parser = parser_class(html_content)
                return parser.parse()

        logger.error("No applicable parser found for the provided HTML.")
        return None