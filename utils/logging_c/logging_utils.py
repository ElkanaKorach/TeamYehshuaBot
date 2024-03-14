import logging, os
from datetime import datetime

class CustomFilter(logging.Filter):
    def filter(self, record):
        # Überprüfe, ob die Nachricht einen bestimmten Text enthält
        if 'HTTP Request: POST https://api.telegram.org/bot6942337491:AAGVKMvHayewt5CUcNFg8xx_zprobgJ4jak' in record.getMessage():
            return False  # Filtere diese Nachrichten aus
        return True  # Zeichne alle anderen Nachrichten auf

def setlogger(lg:logging):
    # Log-Verzeichnis erstellen, falls nicht vorhanden
    if not os.path.exists('log'):
        os.makedirs('log')

    # Konfiguriere das grundlegende Logging-Setup
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f'log/log_{current_time}.log'
    lg.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
    # Erstelle einen Filter und füge ihn dem root Logger hinzu
    filter = CustomFilter()
    lg.getLogger().addFilter(filter)




