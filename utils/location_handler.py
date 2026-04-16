"""
Location Handler
Handles shared locations, weather queries, and timezone lookups.
Uses free APIs: wttr.in (weather), worldtimeapi.org (time)
"""

import asyncio
import logging
from datetime import datetime

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# HTTP timeout
HTTP_TIMEOUT = 10


# ─────────────────────────────────────────────
#  Location message handler
# ─────────────────────────────────────────────

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a location message shared by the user."""
    message = update.message
    loc = message.location
    user = message.from_user

    lat = loc.latitude
    lon = loc.longitude

    # Build map links
    gmaps = f"https://www.google.com/maps?q={lat},{lon}"
    osm = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}"

    # Fetch weather for coordinates
    weather = await _fetch_weather_coords(lat, lon)

    # Fetch address via nominatim (OpenStreetMap reverse geocoding – no key needed)
    address = await _reverse_geocode(lat, lon)

    # Build inline keyboard with map links
    keyboard = [
        [
            InlineKeyboardButton("Google Maps", url=gmaps),
            InlineKeyboardButton("OpenStreetMap", url=osm),
        ]
    ]

    name = user.first_name or "User"
    text = (
        f"<b>Standort von {name}</b>\n\n"
        f"<b>Koordinaten:</b>\n"
        f"  Breitengrad: <code>{lat:.6f}</code>\n"
        f"  Langengrad:  <code>{lon:.6f}</code>\n"
    )
    if address:
        text += f"\n<b>Adresse:</b>\n  {address}\n"

    text += f"\n{weather}"

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


# ─────────────────────────────────────────────
#  /weather [city]
# ─────────────────────────────────────────────

async def get_weather_by_city(city: str) -> str:
    """Return formatted weather string for a city name."""
    return await _fetch_weather_city(city)


# ─────────────────────────────────────────────
#  /time [location]
# ─────────────────────────────────────────────

async def get_time_for_location(location: str) -> str:
    """Return current local time for a given city/timezone name."""
    url = f"https://wttr.in/{location}?format=%Z"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            tz_name = resp.text.strip()
    except Exception as e:
        logger.error(f"Timezone fetch error: {e}")
        tz_name = None

    # Try worldtimeapi for actual time
    time_str = await _fetch_worldtime(location)

    if tz_name:
        return (
            f"<b>Ortszeit fur {location}</b>\n\n"
            f"<b>Zeitzone:</b> {tz_name}\n"
            f"{time_str}"
        )
    return time_str


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

async def _fetch_weather_coords(lat: float, lon: float) -> str:
    """Fetch weather for lat/lon using wttr.in."""
    url = (
        f"https://wttr.in/{lat},{lon}"
        "?format=%l:+%C+%t+%h+%w+%p&lang=de"
    )
    return await _fetch_wttr(url, f"{lat},{lon}")


async def _fetch_weather_city(city: str) -> str:
    """Fetch weather for city name using wttr.in."""
    safe_city = city.replace(" ", "+")
    url = f"https://wttr.in/{safe_city}?format=%l:+%C+%t+%h+%w+%p&lang=de"
    return await _fetch_wttr(url, city)


async def _fetch_wttr(url: str, label: str) -> str:
    """
    Fetch weather from wttr.in and return a formatted HTML string.
    Format codes:
      %l  = location
      %C  = condition description
      %t  = temperature
      %h  = humidity
      %w  = wind
      %p  = precipitation
    """
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            raw = resp.text.strip()
    except Exception as e:
        logger.error(f"wttr.in error: {e}")
        return "<b>Wetter:</b> Konnte nicht geladen werden."

    if not raw or "Unknown" in raw or "Sorry" in raw:
        return f"<b>Wetter:</b> Keine Daten fur {label} gefunden."

    # Full forecast URL
    safe_label = label.replace(" ", "+")
    forecast_url = f"https://wttr.in/{safe_label}"

    return (
        f"<b>Wetter:</b> {raw}\n"
        f'<a href="{forecast_url}">Vollstandige Wettervorhersage</a>'
    )


async def _reverse_geocode(lat: float, lon: float) -> str:
    """Use Nominatim (OSM) to reverse geocode coordinates. Returns address string."""
    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?lat={lat}&lon={lon}&format=json&accept-language=de"
    )
    headers = {"User-Agent": "NazarenerBot/1.0"}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            data = resp.json()
        return data.get("display_name", "")
    except Exception as e:
        logger.error(f"Nominatim error: {e}")
        return ""


async def _fetch_worldtime(location: str) -> str:
    """Try to get current time via worldtimeapi.org for a location name."""
    # Map common German city names to timezone identifiers
    tz_map = {
        "berlin": "Europe/Berlin",
        "wien": "Europe/Vienna",
        "zurich": "Europe/Zurich",
        "zurich": "Europe/Zurich",
        "new york": "America/New_York",
        "london": "Europe/London",
        "paris": "Europe/Paris",
        "moskau": "Europe/Moscow",
        "tokio": "Asia/Tokyo",
        "jerusalem": "Asia/Jerusalem",
        "tel aviv": "Asia/Jerusalem",
        "dubai": "Asia/Dubai",
        "istanbul": "Europe/Istanbul",
    }

    tz = tz_map.get(location.lower())
    if not tz:
        # Try using wttr for a quick timezone offset
        return f"<b>Aktuelle Zeit:</b> Zeitzone nicht erkannt. Nutze /time [IANA Timezone] z.B. /time Europe/Berlin"

    url = f"https://worldtimeapi.org/api/timezone/{tz}"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(url)
            data = resp.json()
        dt_str = data.get("datetime", "")
        if dt_str:
            # Parse ISO format datetime
            dt = datetime.fromisoformat(dt_str)
            return (
                f"<b>Aktuelle Uhrzeit:</b> {dt.strftime('%H:%M:%S')}\n"
                f"<b>Datum:</b> {dt.strftime('%d.%m.%Y')}\n"
                f"<b>Zeitzone:</b> {tz}\n"
                f"<b>UTC Offset:</b> {data.get('utc_offset', '?')}"
            )
    except Exception as e:
        logger.error(f"worldtimeapi error: {e}")

    return f"<b>Zeit fur {location}:</b> Konnte nicht geladen werden."


def request_location_keyboard():
    """Returns a ReplyKeyboardMarkup asking to share location."""
    from telegram import KeyboardButton, ReplyKeyboardMarkup
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Standort teilen", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
