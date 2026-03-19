import sqlite3
from typing import Optional
from app.core.logger import logger

class Database:
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        query = """
                CREATE TABLE IF NOT EXISTS users (
                                                     tg_id INTEGER PRIMARY KEY,
                                                     email TEXT,
                                                     spreadsheet_id TEXT,
                                                     is_active BOOLEAN DEFAULT 1
                ) \
                """
        try:
            with self._get_connection() as conn:
                conn.execute(query)
                conn.commit()
            logger.info("Database tables checked/created successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def register_user(self, tg_id: int, email: str, sheet_id: str):
        query = """
                INSERT INTO users (tg_id, email, spreadsheet_id)
                VALUES (?, ?, ?)
                    ON CONFLICT(tg_id) DO UPDATE SET
                    email=excluded.email,
                                              spreadsheet_id=excluded.spreadsheet_id \
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

db = Database()