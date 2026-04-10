"""
Database Manager — erweitert um scheduled_messages, group_settings, chats
"""

import sqlite3
import json
import logging
from datetime import datetime

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
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # ─────────────────────────────────────────
    #  Schema
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

            # Warnings
            c.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    reason  TEXT
                )
            """)

            # Per-chat settings (rules, welcome, …)
            c.execute("""
                CREATE TABLE IF NOT EXISTS group_settings (
                    chat_id INTEGER NOT NULL,
                    key     TEXT    NOT NULL,
                    value   TEXT,
                    PRIMARY KEY (chat_id, key)
                )
            """)

            # Known chats (für Broadcast / Dropdown im Web)
            c.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id       INTEGER PRIMARY KEY,
                    title         TEXT,
                    chat_type     TEXT,
                    registered_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scheduled messages
            c.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_messages (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id          INTEGER NOT NULL,
                    message_type     TEXT    NOT NULL DEFAULT 'text',
                    content          TEXT,
                    caption          TEXT,
                    media_url        TEXT,
                    media_file_id    TEXT,
                    media_local_path TEXT,
                    buttons_json     TEXT,
                    scheduled_at     TEXT    NOT NULL,
                    status           TEXT    DEFAULT 'pending',
                    created_at       TEXT    DEFAULT CURRENT_TIMESTAMP,
                    sent_at          TEXT,
                    error_message    TEXT
                )
            """)

            conn.commit()
            logger.info("DB tables verified.")

    # ─────────────────────────────────────────
    #  Whitelist
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
                    c.execute(f"INSERT OR IGNORE INTO {table_name} (userid) VALUES (?)", (uid,))
                except Exception as e:
                    logger.error(f"Insert {table_name} uid={uid}: {e}")
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
    #  Warnings
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
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "DELETE FROM warnings WHERE id = ("
                "SELECT id FROM warnings WHERE user_id = ? ORDER BY id DESC LIMIT 1)",
                (user_id,),
            )
            conn.commit()

    def reset_warnings(self, user_id: int):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))
            conn.commit()

    def set_warnings(self, user_id: int, count: int):
        self.reset_warnings(user_id)

    def get_all_warnings(self) -> list:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT user_id, chat_id, COUNT(*) as cnt, MAX(reason) as last_reason
                FROM warnings GROUP BY user_id, chat_id
            """)
            return [dict(r) for r in c.fetchall()]

    # ─────────────────────────────────────────
    #  Group settings
    # ─────────────────────────────────────────

    def get_setting(self, chat_id: int, key: str) -> str:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT value FROM group_settings WHERE chat_id=? AND key=?",
                (chat_id, key),
            )
            row = c.fetchone()
            return row[0] if row else ""

    def set_setting(self, chat_id: int, key: str, value: str):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO group_settings (chat_id, key, value) VALUES (?,?,?)",
                (chat_id, key, value),
            )
            conn.commit()

    def get_all_settings(self) -> list:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT chat_id, key, value FROM group_settings")
            return [dict(r) for r in c.fetchall()]

    # ─────────────────────────────────────────
    #  Chat registry
    # ─────────────────────────────────────────

    def register_chat(self, chat_id: int, title: str = "", chat_type: str = ""):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO chats (chat_id, title, chat_type) VALUES (?,?,?)",
                (chat_id, title, chat_type),
            )
            conn.commit()

    def get_all_chats(self) -> list:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT chat_id, title, chat_type, registered_at FROM chats")
            return [dict(r) for r in c.fetchall()]

    # ─────────────────────────────────────────
    #  Scheduled messages
    # ─────────────────────────────────────────

    def add_scheduled_message(
        self,
        chat_id: int,
        message_type: str,
        scheduled_at: str,
        content: str = None,
        caption: str = None,
        media_url: str = None,
        media_file_id: str = None,
        media_local_path: str = None,
        buttons_json: str = None,
    ) -> int:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO scheduled_messages
                   (chat_id, message_type, content, caption,
                    media_url, media_file_id, media_local_path,
                    buttons_json, scheduled_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    chat_id, message_type, content, caption,
                    media_url, media_file_id, media_local_path,
                    buttons_json, scheduled_at,
                ),
            )
            conn.commit()
            return c.lastrowid

    def get_scheduled_messages(self, status: str = None) -> list:
        with self.create_connection() as conn:
            c = conn.cursor()
            if status:
                c.execute(
                    "SELECT * FROM scheduled_messages WHERE status=? ORDER BY scheduled_at",
                    (status,),
                )
            else:
                c.execute("SELECT * FROM scheduled_messages ORDER BY scheduled_at DESC")
            return [dict(r) for r in c.fetchall()]

    def get_scheduled_message(self, msg_id: int) -> dict:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM scheduled_messages WHERE id=?", (msg_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_due_scheduled_messages(self) -> list:
        """Return pending messages whose scheduled_at <= now."""
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM scheduled_messages WHERE status='pending' AND scheduled_at <= ?",
                (now,),
            )
            return [dict(r) for r in c.fetchall()]

    def mark_message_sent(self, msg_id: int):
        now = datetime.utcnow().isoformat()
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE scheduled_messages SET status='sent', sent_at=? WHERE id=?",
                (now, msg_id),
            )
            conn.commit()

    def mark_message_failed(self, msg_id: int, error: str):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE scheduled_messages SET status='failed', error_message=? WHERE id=?",
                (error, msg_id),
            )
            conn.commit()

    def cancel_scheduled_message(self, msg_id: int):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE scheduled_messages SET status='cancelled' WHERE id=? AND status='pending'",
                (msg_id,),
            )
            conn.commit()

    def delete_scheduled_message(self, msg_id: int):
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM scheduled_messages WHERE id=?", (msg_id,))
            conn.commit()

    def get_stats(self) -> dict:
        with self.create_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT status, COUNT(*) as cnt FROM scheduled_messages GROUP BY status")
            rows = {r[0]: r[1] for r in c.fetchall()}
            c.execute("SELECT COUNT(*) FROM chats")
            chats_total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM warnings")
            warnings_total = c.fetchone()[0]
        return {
            "pending":  rows.get("pending",   0),
            "sent":     rows.get("sent",       0),
            "failed":   rows.get("failed",     0),
            "cancelled":rows.get("cancelled",  0),
            "chats":    chats_total,
            "warnings": warnings_total,
        }


# Module-level singleton
db_manager = DatabaseManager()
