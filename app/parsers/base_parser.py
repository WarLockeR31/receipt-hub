from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from app.models.receipt import Receipt

class BaseReceiptParser(ABC):
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.html_content = html_content

    @classmethod
    @abstractmethod
    def is_applicable(cls, html_content: str, soup: BeautifulSoup) -> bool:
        pass

    @abstractmethod
    def parse(self) -> Receipt:
        pass