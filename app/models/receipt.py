from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum

class Unit(Enum):
    PC = "шт"
    KG = "кг"
    LITER = "л"
    PACK = "уп"
    UNKNOWN = "н/д"

class StoreType(Enum):
    PYATEROCHKA = "Пятёрочка"
    MAGNIT = "Магнит"
    OTHER = "Прочее"

@dataclass
class ReceiptItem:
    name: str
    price: float
    quantity: float
    sum: float
    unit: Unit = Unit.PC
    category: str = "Прочее"

@dataclass
class Receipt:
    id: str
    datetime: datetime
    store: StoreType
    total_sum: float
    items: List[ReceiptItem] = field(default_factory=list)
    raw_data: Optional[str] = None