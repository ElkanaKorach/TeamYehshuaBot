# Basierend auf einem benutzerdefinierten Python-3.9-Image
FROM ggvick/python3.9

# Setzen des Arbeitsverzeichnisses im Container
WORKDIR /app

# Füge das Python-Skript und alle anderen notwendigen Dateien und Verzeichnisse zum Docker-Container hinzu
ADD main_bot.py .
ADD utils/ ./utils/
ADD configs/ ./configs/
ADD database/ ./database/
ADD log/ ./log/
ADD logging/ ./logging/

# Switch to root user
USER root

# Installiere die benötigten Pakete
RUN apt-get update -y && \
    apt-get install -y nano

# Python package installation
RUN pip install --upgrade pip && \
    pip install python-telegram-bot

# Führe das Python-Skript aus
CMD ["python", "./main_bot.py"]
