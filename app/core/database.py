import sqlite3
from pathlib import Path
from typing import Optional
from app.core.logger import logger
from app.models.receipt import Receipt

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Database:
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = BASE_DIR / db_path
        self._create_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _create_tables(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                email TEXT UNIQUE,
                spreadsheet_id TEXT,
                is_active BOOLEAN DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS receipts (
                id TEXT PRIMARY KEY, 
                user_id INTEGER,
                datetime TEXT,
                store_name TEXT,
                total_sum REAL,
                raw_data TEXT,
                FOREIGN KEY (user_id) REFERENCES users (tg_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id TEXT,
                name TEXT,
                price REAL,
                quantity REAL,
                sum REAL,
                unit TEXT,
                category TEXT,
                FOREIGN KEY (receipt_id) REFERENCES receipts (id) ON DELETE CASCADE
            )
            """
        ]

        try:
            with self._get_connection() as conn:
                for query in queries:
                    conn.execute(query)
                conn.commit()
            logger.info("Database tables checked/created successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    # User methods
    def register_user(self, tg_id: int, email: str, sheet_id: str):
        query = """
        INSERT INTO users (tg_id, email, spreadsheet_id)
        VALUES (?, ?, ?) ON CONFLICT (tg_id) DO
        UPDATE SET
            email=excluded.email,
            spreadsheet_id=excluded.spreadsheet_id
        """
        try:
            with self._get_connection() as conn:
                conn.execute(query, (tg_id, email, sheet_id))
                conn.commit()
            logger.info(f"User {tg_id} registered/updated successfully.")
        except Exception as e:
            logger.error(f"Error registering user {tg_id}: {e}")

    def get_user_by_email(self, email: str) -> Optional[tuple]:
        query = "SELECT tg_id, spreadsheet_id FROM users WHERE email = ? AND is_active = 1"
        try:
            with self._get_connection() as conn:
                return conn.execute(query, (email,)).fetchone()
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}")
            return None

    def get_user_by_tg_id(self, tg_id: int) -> Optional[tuple]:
        query = "SELECT email, spreadsheet_id FROM users WHERE tg_id = ? AND is_active = 1"
        try:
            with self._get_connection() as conn:
                return conn.execute(query, (tg_id,)).fetchone()
        except Exception as e:
            logger.error(f"Error fetching user by tg_id {tg_id}: {e}")
            return None

    # Receipt methods
    def save_receipt(self, tg_id: int, receipt: Receipt) -> bool:
        receipt_query = """
        INSERT INTO receipts (id, user_id, datetime, store_name, total_sum, raw_data)
        VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO NOTHING
        """

        item_query = """
        INSERT INTO items (receipt_id, name, price, quantity, sum, unit, category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    receipt_query,
                    (receipt.id, tg_id, receipt.datetime.isoformat(),
                     receipt.store.value, receipt.total_sum, receipt.raw_data)
                )

                if cursor.rowcount == 0:
                    logger.info(f"Receipt {receipt.id} already exists in DB. Skipping.")
                    return False

                for item in receipt.items:
                    conn.execute(
                        item_query,
                        (receipt.id, item.name, item.price, item.quantity,
                         item.sum, item.unit.value, item.category)
                    )

            logger.info(f"Successfully saved receipt {receipt.id} with {len(receipt.items)} items.")
            return True

        except Exception as e:
            logger.error(f"Failed to save receipt {receipt.id}: {e}")
            return False

db = Database()