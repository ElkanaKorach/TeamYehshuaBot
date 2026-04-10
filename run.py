"""
run.py — Startet Bot und Web-Interface gleichzeitig.

Verwendung:
    python run.py

Der Telegram-Bot läuft im Haupt-Thread (asyncio).
Das Flask-Web-Interface läuft in einem Daemon-Thread.
Beide teilen dieselbe SQLite-Datenbank.
"""

import logging
import threading

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def run_web():
    """Flask-Web-Interface starten."""
    try:
        from configs.config import WEB_PORT
    except ImportError:
        WEB_PORT = 5000

    from web.app import app
    logger.info(f"Web-Interface startet auf http://0.0.0.0:{WEB_PORT}")
    # use_reloader=False ist wichtig, damit kein zweiter Thread gestartet wird
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False, use_reloader=False)


def run_bot():
    """Telegram-Bot starten (blockierend)."""
    from channel_help_bot import main
    logger.info("Telegram-Bot startet...")
    main()


if __name__ == "__main__":
    # Web-Interface als Daemon-Thread (endet automatisch wenn Bot endet)
    web_thread = threading.Thread(target=run_web, daemon=True, name="WebInterface")
    web_thread.start()

    # Bot im Haupt-Thread (run_polling ist blockierend)
    run_bot()
