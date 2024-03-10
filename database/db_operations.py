import sqlite3
import logging

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_PATH = 'local_db.sqlite3'

class DatabaseManager:
    def __init__(self):
        self.create_tables()
        # Initialisiere Whitelists
        self.whitelistsozialmedia = self.get_list("whitelistsozialmedia")
        self.whitelistmale = self.get_list("whitelistmale")
        self.whitelistfemale = self.get_list("whitelistfemale")
        self.whitelistparascha = self.get_list("whitelistparascha")
        self.whitelistprojekte = self.get_list("whitelistprojekte")

    def create_connection(self):
        try:
            connection = sqlite3.connect(DATABASE_PATH)
            logger.info("Erfolgreich mit der Datenbank verbunden.")
            return connection
        except Exception as e:
            logger.error(f"Verbindung zur Datenbank nicht möglich! Grund: {str(e)}")
            raise

    def create_tables(self):
        # Erstelle Tabellen
        with self.create_connection() as conn:
            cursor = conn.cursor()
            # Erstellen verschiedener Tabellen
            cursor.execute('''CREATE TABLE IF NOT EXISTS whitelistsozialmedia (userid INTEGER PRIMARY KEY)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS whitelistmale (userid INTEGER PRIMARY KEY)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS whitelistfemale (userid INTEGER PRIMARY KEY)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS whitelistparascha (userid INTEGER PRIMARY KEY)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS whitelistprojekte (userid INTEGER PRIMARY KEY)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS whitelistinfo (userid INTEGER PRIMARY KEY)''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    reason TEXT
                )
            ''')
            conn.commit()
            logger.info("Tabellen erfolgreich erstellt/überprüft.")

    def get_list(self, table_name):
        # Hole Liste aus Tabelle
        with self.create_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(f"SELECT userid FROM {table_name}")
            return [row[0] for row in cursor.fetchall()]

    def save_list_to_table(self, table_name, user_ids):
        # Speichere Liste in Tabelle
        with self.create_connection() as connection:
            cursor = connection.cursor()
            for user_id in user_ids:
                try:
                    cursor.execute(f"INSERT OR IGNORE INTO {table_name} (userid) VALUES (?)", (user_id,))
                    connection.commit()
                    logger.info(f"User ID {user_id} erfolgreich in {table_name} eingefügt.")
                except Exception as e:
                    logger.error(f"Fehler beim Einfügen von User ID {user_id} in {table_name}. Grund: {str(e)}")

    def clear_list_table(self, table_name):
        # Leere Tabelle
        with self.create_connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(f"DELETE FROM {table_name}")
                connection.commit()
                logger.info(f"Whitelist {table_name} wurde erfolgreich geleert.")
            except Exception as e:
                logger.error(f"Fehler beim Leeren der Whitelist {table_name}. Grund: {str(e)}")

    def get_warnings(self, user_id):
        # Hole Warnungen für einen Benutzer
        with self.create_connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
                warnings_count = cursor.fetchone()[0]
                logger.info(f"Anzahl der Warnungen für User ID {user_id} ist {warnings_count}.")
                return warnings_count
            except Exception as e:
                logger.error(f"Fehler beim Abrufen der Warnungen für User ID {user_id}. Grund: {str(e)}")
                return 0

    def set_warnings(self, user_id, warnings_count):
        with self.create_connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("UPDATE warnings SET warnings_count = ? WHERE user_id = ?", (warnings_count, user_id))
                connection.commit()
                logger.info(f"Anzahl der Warnungen für User ID {user_id} erfolgreich auf {warnings_count} gesetzt.")
            except Exception as e:
                logger.error(f"Fehler beim Setzen der Warnungen für User ID {user_id}. Grund: {str(e)}")

    def add_warning(self, user_id, chat_id, reason):
        # Füge eine Warnung für einen Benutzer hinzu
        with self.create_connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("INSERT INTO warnings (user_id, chat_id, reason) VALUES (?, ?, ?)", (user_id, chat_id, reason))
                connection.commit()
                logger.info(f"Warnung für User ID {user_id} erfolgreich hinzugefügt.")
            except Exception as e:
                logger.error(f"Fehler beim Hinzufügen einer Warnung für User ID {user_id}. Grund: {str(e)}")

# Initialisiere Datenbank-Manager
db_manager = DatabaseManager()
