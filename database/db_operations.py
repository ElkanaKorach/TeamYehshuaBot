"""
Database Manager
SQLite-backed persistence for the TeamYehshua Telegram bot.

Tables:
  whitelistsozialmedia  – user IDs for social-media topic
  whitelistmale         – user IDs for men's topic
  whitelistfemale       – user IDs for women's topic
  whitelistparascha     – user IDs for parascha topic
  whitelistprojekte     – user IDs for projects topic
  whitelistinfo         – user IDs for info topic
  warnings              – per-user warning records
  group_settings        – per-chat key/value settings (rules, welcome, …)
  chats                 – registry of all chats the bot has seen
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATABASE_PATH = "local_db.sqlite3"


class DatabaseManager:
    def __init__(self):
        self.create_tables()

    # ─────────────────────────────────────────
    #  Connection
    # ─────────────────────────────────────────

    def create_connection(self):
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            return conn
        except Exception as e:
            logger.error(f"DB connection failed: {e}")
            raise

    # ─────────────────────────────────────────
    #  Schema creation
    # ─────────────────────────────────────────

    def create_tables(self):
        with self.create_connection() as conn:
            c = conn.cursor()
            # Whitelist tables
            for tbl in (
                "whitelistsozialmedia",
                "whitelistmale",
                "whitelistfemale",
                "whitelistparascha",
                "whitelistprojekte",
                "whitelistinfo",
            ):
                c.execute(f"CREATE TABLE IF NOT EXISTS {tbl} (userid INTEGER PRIMARY KEY)")

            # Warnings table
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS warnings (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    reason  TEXT
                )
                """
            )

            # Per-chat settings (rules, welcome message, …)
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS group_settings (
                    chat_id INTEGER NOT NULL,
                    key     TEXT    NOT NULL,
                    value   TEXT,
                    PRIMARY KEY (chat_id, key)
                )
                """
            )

            # Chat registry (for broadcast)
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    title   TEXT,
                    registered_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()
            logger.info("Database tables verified/created.")

    # ─────────────────────────────────────────
    #  Whitelist helpers
    # ─────────────────────────────────────────

    def get_list(self, table_name: str) -> list:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(f"SELECT userid FROM {table_name}")
            return [row[0] for row in c.fetchall()]

    def save_list_to_table(self, table_name: str, user_ids: list):
        with self.create_connection() as conn:
            c = conn.cursor()
            for uid in user_ids:
                try:
                    c.execute(
                        f"INSERT OR IGNORE INTO {table_name} (userid) VALUES (?)", (uid,)
                    )
                except Exception as e:
                    logger.error(f"Insert into {table_name} failed for {uid}: {e}")
            conn.commit()

    def remove_from_list(self, table_name: str, user_id: int):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(f"DELETE FROM {table_name} WHERE userid = ?", (user_id,))
            conn.commit()

    def clear_list_table(self, table_name: str):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(f"DELETE FROM {table_name}")
            conn.commit()

    # ─────────────────────────────────────────
    #  Warning helpers
    # ─────────────────────────────────────────

    def get_warnings(self, user_id: int) -> int:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
            return c.fetchone()[0]

    def add_warning(self, user_id: int, chat_id: int, reason: str):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO warnings (user_id, chat_id, reason) VALUES (?, ?, ?)",
                (user_id, chat_id, reason),
            )
            conn.commit()

    def remove_last_warning(self, user_id: int):
        """Delete the most recent warning for a user."""
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM warnings WHERE id = ("
                "  SELECT id FROM warnings WHERE user_id = ? ORDER BY id DESC LIMIT 1"
                ")",
                (user_id,),
            )
            conn.commit()

    def reset_warnings(self, user_id: int):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))
            conn.commit()

    # Legacy compatibility
    def set_warnings(self, user_id: int, count: int):
        self.reset_warnings(user_id)

    # ─────────────────────────────────────────
    #  Group settings helpers
    # ─────────────────────────────────────────

    def get_setting(self, chat_id: int, key: str) -> str:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT value FROM group_settings WHERE chat_id = ? AND key = ?",
                (chat_id, key),
            )
            row = c.fetchone()
            return row[0] if row else ""

    def set_setting(self, chat_id: int, key: str, value: str):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO group_settings (chat_id, key, value) VALUES (?, ?, ?)",
                (chat_id, key, value),
            )
            conn.commit()

    # ─────────────────────────────────────────
    #  Chat registry helpers
    # ─────────────────────────────────────────

    def register_chat(self, chat_id: int, title: str = ""):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO chats (chat_id, title) VALUES (?, ?)",
                (chat_id, title),
            )
            conn.commit()

    def get_all_chats(self) -> list:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT chat_id FROM chats")
            return [row[0] for row in c.fetchall()]


# Module-level singleton
db_manager = DatabaseManager()
