# Nazarener Bot

Telegram-Gruppen-Verwaltungsbot mit Web-Interface, Nachrichten-Planer, Standort/Wetter und vollständiger Moderations-Suite.

---

## Funktionen

| Bereich | Features |
|---|---|
| **Moderation** | Ban, Unban, Kick, Mute, Unmute, Warn (Auto-Ban bei 3x), Unwarn |
| **Whitelist** | 5 Kategorien (Frauen, Männer, SozialMedia, Parascha, Info) |
| **Standort** | Standort teilen → Karte + Adresse + Wetter + OpenStreetMap/Google Maps |
| **Wetter** | `/weather [Ort]` — live via wttr.in (kein API-Key nötig) |
| **Nachrichten-Planer** | Text, Bild, Video, Datei, Audio; Telegram-Buttons; täglich/wöchentlich/monatlich |
| **Web-Interface** | Dashboard, Nachrichten verwalten, Einstellungen, Whitelist, Verwarnungen |
| **Vorlagen** | Nachrichten-Vorlagen speichern und wiederverwenden |
| **Willkommen** | Automatisch + anpassbar pro Gruppe |

---

## Voraussetzungen

- Python **3.10+**
- Ein Telegram-Bot-Token von [@BotFather](https://t.me/BotFather)
- Linux/macOS/Windows — kein externer Datenbankserver nötig (SQLite)

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/ElkanaKorach/TeamYehshuaBot.git
cd TeamYehshuaBot
# Oder wenn das Repo umbenannt wurde:
# git clone https://github.com/ElkanaKorach/NazarenerBot.git
# cd NazarenerBot
```

### 2. Virtuelle Umgebung erstellen und aktivieren

```bash
python3 -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. Konfiguration anpassen

Öffne `configs/config.py` und trage deine Werte ein:

```python
TOKEN = 'DEIN_BOT_TOKEN_HIER'        # Token von @BotFather

# Web-Interface
WEB_PORT       = 5000                 # Port (Standard: 5000)
WEB_PASSWORD   = 'sicheres_passwort' # Login-Passwort für das Web-Interface
WEB_SECRET_KEY = 'zufaelliger_key'   # Beliebige zufällige Zeichenkette

# Gruppen-Topic-Namen (so wie sie in deiner Gruppe heißen)
GENERAL_CHAT_MESSAGE_ID    = "Parasha"
SOZIALMEDIA_CHAT_MESSAGE_ID = "Social Media"
MALE_CHAT_MESSAGE_ID       = "Männer Gruppe"
FEMALE_CHAT_MESSAGE_ID     = "Frauen Gruppe"
INFO_CHAT_MESSAGE_ID       = "Infos"
```

> **Sicherheitshinweis:** Committe `config.py` niemals mit echtem Token in ein öffentliches Repository!

---

## Starten

### Bot + Web-Interface zusammen (empfohlen)

```bash
python run.py
```

- **Telegram-Bot** startet automatisch
- **Web-Interface** erreichbar unter `http://localhost:5000`

### Nur Bot (ohne Web-Interface)

```bash
python channel_help_bot.py
```

### Nur Web-Interface (nur zur Konfiguration)

```bash
python web/app.py
```

---

## Web-Interface

Nach dem Start unter `http://localhost:5000` erreichbar.

Login mit dem Passwort aus `configs/config.py` → `WEB_PASSWORD`.

| Seite | URL | Beschreibung |
|---|---|---|
| Dashboard | `/dashboard` | Statistiken, letzte Nachrichten, Chats |
| Nachrichten | `/messages` | Alle geplanten Nachrichten |
| Neue Nachricht | `/messages/add` | Nachricht planen (Text/Bild/Video/Datei/Audio) |
| Vorlagen | `/templates` | Nachrichten-Vorlagen verwalten |
| Einstellungen | `/settings` | Regeln & Willkommensnachrichten pro Gruppe |
| Whitelist | `/whitelist` | Alle Kategorien verwalten |
| Verwarnungen | `/warnings` | Verwarnungen anzeigen und zurücksetzen |

---

## Bot-Befehle

### Allgemein
| Befehl | Beschreibung |
|---|---|
| `/start` | Willkommen + Inline-Menü |
| `/help` | Alle Befehle |
| `/id` | Eigene oder fremde User-ID |
| `/info` | Benutzerinfo (Name, ID, Verwarnungen) |
| `/rules` | Gruppenregeln anzeigen |
| `/stats` | Gruppenstatistiken |
| `/roll` | Würfeln (1–6) |
| `/coinflip` | Münze werfen |

### Standort & Wetter
| Befehl | Beschreibung |
|---|---|
| `/location` | Standort per Schaltfläche teilen → Karte + Wetter |
| `/weather [Ort]` | Aktuelles Wetter |
| `/time [Ort]` | Aktuelle Ortszeit |

### Nachrichten planen (Telegram)
| Befehl | Beschreibung |
|---|---|
| `/schedule` | Neue Nachricht planen (geführter Dialog) |
| `/schedules` | Ausstehende Nachrichten für diesen Chat anzeigen |
| `/cancelschedule <ID>` | Geplante Nachricht abbrechen |

### Admin-Befehle
| Befehl | Beschreibung |
|---|---|
| `/ban` | User bannen (Reply oder ID) |
| `/unban <ID>` | User entbannen |
| `/kick` | User kicken |
| `/mute [Minuten]` | Stummschalten (Standard: 60 min) |
| `/unmute` | Entstummen |
| `/warn` | Verwarnen (nach 3× Auto-Ban) |
| `/unwarn` | Letzte Verwarnung entfernen |
| `/warnings` | Verwarnungsstand anzeigen |
| `/pin` | Replied-Nachricht pinnen |
| `/unpin` | Alle Pins entfernen |
| `/setrules` | Gruppenregeln setzen |
| `/setwelcome` | Willkommensnachricht setzen (Variablen: `{name}`, `{id}`, `{chat}`) |
| `/whitelist [typ]` | User whitelisten (frau/mann/sozialmedia/parascha/info) |
| `/removefromwhitelist [typ]` | User entfernen |
| `/broadcast` | Nachricht an alle Chats senden |

---

## Als Systemdienst (Linux, optional)

Damit der Bot nach einem Neustart automatisch startet:

```bash
sudo nano /etc/systemd/system/nazarener.service
```

Inhalt:
```ini
[Unit]
Description=Nazarener Telegram Bot
After=network.target

[Service]
User=DEIN_BENUTZER
WorkingDirectory=/pfad/zu/TeamYehshuaBot
ExecStart=/pfad/zu/TeamYehshuaBot/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable nazarener
sudo systemctl start nazarener

# Status prüfen
sudo systemctl status nazarener
```

---

## Mit Docker (optional)

```bash
docker build -t nazarener-bot .
docker run -d \
  --name nazarener \
  -p 5000:5000 \
  -v $(pwd)/local_db.sqlite3:/app/local_db.sqlite3 \
  -v $(pwd)/web/uploads:/app/web/uploads \
  nazarener-bot
```

---

## Projektstruktur

```
NazarenerBot/
├── run.py                  ← Startpunkt (Bot + Web zusammen)
├── channel_help_bot.py     ← Telegram-Bot (alle Befehle)
├── configs/
│   └── config.py           ← Token, Passwort, Einstellungen
├── database/
│   └── db_operations.py    ← SQLite-Datenbank
├── scheduler/
│   └── scheduler.py        ← Nachrichten-Planer (JobQueue)
├── utils/
│   ├── location_handler.py ← Standort, Wetter, Karte
│   └── welcome_handler.py  ← Willkommen/Abschied
├── web/
│   ├── app.py              ← Flask Web-Interface
│   ├── templates/          ← HTML-Templates (Bootstrap 5)
│   └── uploads/            ← Hochgeladene Mediendateien
└── requirements.txt
```

---

## Lizenz

Privat / Intern — Nazarener
