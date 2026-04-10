"""
TeamYehshua Channel Help Bot
Comprehensive Telegram Group Management Bot inspired by @channelhelp
Features: Moderation, Location, Weather, Welcome, Anti-Spam, Inline Menus
"""

import asyncio
import logging
import re
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from configs.config import TOKEN
from database.db_operations import DatabaseManager
from scheduler.scheduler import check_and_send_scheduled
from utils.location_handler import (
    handle_location,
    get_weather_by_city,
    get_time_for_location,
    request_location_keyboard,
)
from utils.welcome_handler import (
    handle_new_member,
    handle_left_member,
    get_group_rules,
    set_group_rules,
    get_welcome_message,
    set_welcome_message,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

db = DatabaseManager()

# Bot superadmins (can use bot in private as well)
BOT_ADMINS = [1082436365, 1438346474]
MAX_WARNINGS = 3

# ConversationHandler states
AWAITING_RULES = 1
AWAITING_WELCOME = 2
AWAITING_BROADCAST = 3


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

async def _is_admin(bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


async def _get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return (user_id, username) from reply or first argument."""
    msg = update.message
    if msg.reply_to_message:
        u = msg.reply_to_message.from_user
        return u.id, u.first_name
    if context.args:
        try:
            uid = int(context.args[0])
            return uid, str(uid)
        except ValueError:
            pass
    return None, None


def _mention(user) -> str:
    name = (user.first_name or "User").replace("<", "&lt;")
    return f'<a href="tg://user?id={user.id}">{name}</a>'


async def _admin_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Reply with error and return False if caller is not admin."""
    if update.effective_chat.type == "private":
        return update.effective_user.id in BOT_ADMINS
    if not await _is_admin(context.bot, update.effective_chat.id, update.effective_user.id):
        msg = await update.message.reply_text(
            "Du hast keine Berechtigung fur diesen Befehl."
        )
        await asyncio.sleep(5)
        try:
            await msg.delete()
            await update.message.delete()
        except Exception:
            pass
        return False
    return True


# ─────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("Hilfe & Befehle", callback_data="help"),
            InlineKeyboardButton("Gruppeninfo", callback_data="info"),
        ],
        [
            InlineKeyboardButton("Regeln", callback_data="rules"),
            InlineKeyboardButton("Standort teilen", callback_data="request_location"),
        ],
        [
            InlineKeyboardButton("Admin Befehle", callback_data="admin_help"),
        ],
    ]
    text = (
        f"Schalom {_mention(user)}! \n\n"
        "<b>TeamYehshua Bot</b> – dein Gruppen-Assistent.\n\n"
        "<b>Funktionen:</b>\n"
        "• Moderation (Ban / Mute / Warn)\n"
        "• Standort, Wetter & Uhrzeit\n"
        "• Willkommens-Nachrichten\n"
        "• Anti-Spam Schutz\n"
        "• Gruppen-Statistiken\n\n"
        "Wahle eine Option oder tippe /help."
    )
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


# ─────────────────────────────────────────────
#  /help
# ─────────────────────────────────────────────

HELP_TEXT = (
    "<b>Verfugbare Befehle</b>\n\n"
    "<b>Allgemein</b>\n"
    "/start – Bot starten\n"
    "/help – Diese Hilfe\n"
    "/id – Deine User-ID\n"
    "/info – Benutzerinfo\n"
    "/rules – Gruppenregeln\n"
    "/stats – Gruppenstatistiken\n\n"
    "<b>Standort & Wetter</b>\n"
    "/location – Standort teilen (Karte + Wetter)\n"
    "/weather [Ort] – Wetter abfragen\n"
    "/time [Ort] – Ortszeit abfragen\n\n"
    "<b>Unterhaltung</b>\n"
    "/roll – Wurfeln (1-6)\n"
    "/coinflip – Munze werfen\n\n"
    "<b>Admin</b>\n"
    "/ban – User bannen\n"
    "/unban – User entbannen\n"
    "/kick – User kicken\n"
    "/mute [Minuten] – User stummschalten\n"
    "/unmute – User entstummen\n"
    "/warn – User verwarnen\n"
    "/unwarn – Verwarnung entfernen\n"
    "/warnings – Verwarnungen anzeigen\n"
    "/pin – Nachricht pinnen\n"
    "/unpin – Alle Pins entfernen\n"
    "/setrules – Gruppenregeln setzen\n"
    "/setwelcome – Willkommensnachricht setzen\n"
    "/broadcast – Nachricht senden\n"
    "/whitelist [typ] – User whitelisten\n"
    "/removefromwhitelist [typ] – Entfernen\n"
)

ADMIN_HELP_TEXT = (
    "<b>Admin Befehle im Detail</b>\n\n"
    "<b>/ban</b> – Antworte auf Nachricht oder gib ID an\n"
    "<b>/unban</b> [user_id] – User entbannen\n"
    "<b>/kick</b> – Antworte auf Nachricht\n"
    "<b>/mute</b> [min] – Stummschalten (Standard: 60 min)\n"
    "<b>/unmute</b> – Entstummen\n"
    "<b>/warn</b> – Verwarnen (nach 3: Auto-Ban)\n"
    "<b>/unwarn</b> – Letzte Verwarnung entfernen\n"
    "<b>/warnings</b> – Alle Verwarnungen anzeigen\n"
    "<b>/pin</b> – Antworte auf Nachricht zum Pinnen\n"
    "<b>/setrules</b> – Neue Regeln eingeben\n"
    "<b>/setwelcome</b> – Neue Willkommensnachricht\n"
    "  Variablen: {name}, {id}, {chat}\n"
    "<b>/broadcast</b> – Nachricht an alle\n"
    "<b>/whitelist</b> frau|mann|sozialmedia|parascha|info\n"
    "<b>/removefromwhitelist</b> – Selbe Kategorien\n"
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Hauptmenu", callback_data="main_menu")]]
    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


# ─────────────────────────────────────────────
#  Utility commands
# ─────────────────────────────────────────────

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        text = (
            f"<b>User-ID:</b> <code>{target.id}</code>\n"
            f"<b>Name:</b> {target.first_name}"
        )
    else:
        text = (
            f"<b>Deine User-ID:</b> <code>{user.id}</code>\n"
            f"<b>Chat-ID:</b> <code>{chat.id}</code>"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else user

    warnings = db.get_warnings(target.id)
    username = f"@{target.username}" if target.username else "–"
    lang = target.language_code or "–"

    text = (
        f"<b>Benutzerinfo</b>\n\n"
        f"<b>Name:</b> {target.first_name} {target.last_name or ''}\n"
        f"<b>Username:</b> {username}\n"
        f"<b>ID:</b> <code>{target.id}</code>\n"
        f"<b>Sprache:</b> {lang}\n"
        f"<b>Bot:</b> {'Ja' if target.is_bot else 'Nein'}\n"
        f"<b>Verwarnungen:</b> {warnings}/{MAX_WARNINGS}\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    try:
        count = await context.bot.get_chat_member_count(chat.id)
    except Exception:
        count = "?"
    admins = await context.bot.get_chat_administrators(chat.id)
    text = (
        f"<b>Gruppenstatistiken</b>\n\n"
        f"<b>Name:</b> {chat.title or chat.first_name}\n"
        f"<b>ID:</b> <code>{chat.id}</code>\n"
        f"<b>Mitglieder:</b> {count}\n"
        f"<b>Admins:</b> {len(admins)}\n"
        f"<b>Typ:</b> {chat.type}\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = get_group_rules(update.effective_chat.id)
    if not rules:
        rules = "Noch keine Regeln gesetzt. Ein Admin kann mit /setrules Regeln setzen."
    keyboard = [[InlineKeyboardButton("Hauptmenu", callback_data="main_menu")]]
    await update.message.reply_text(
        f"<b>Gruppenregeln</b>\n\n{rules}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


async def cmd_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    result = random.randint(1, 6)
    faces = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6"}
    await update.message.reply_text(
        f"Wurfel-Ergebnis: <b>{faces[result]}</b> ({result})",
        parse_mode=ParseMode.HTML,
    )


async def cmd_coinflip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import random
    result = random.choice(["Kopf", "Zahl"])
    await update.message.reply_text(
        f"Munze: <b>{result}</b>",
        parse_mode=ParseMode.HTML,
    )


# ─────────────────────────────────────────────
#  Location & Weather commands
# ─────────────────────────────────────────────

async def cmd_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to share their location via reply keyboard."""
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Standort teilen", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    await update.message.reply_text(
        "Bitte teile deinen Standort uber die Schaltflache unten.\n"
        "Der Bot zeigt dir dann Karte, Wetter und Ortszeit.",
        reply_markup=keyboard,
    )


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Bitte gib einen Ort an: /weather Berlin"
        )
        return
    city = " ".join(context.args)
    msg = await update.message.reply_text(f"Lade Wetterdaten fur {city}...")
    result = await get_weather_by_city(city)
    await msg.edit_text(result, parse_mode=ParseMode.HTML)


async def cmd_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Bitte gib einen Ort an: /time Berlin"
        )
        return
    location = " ".join(context.args)
    msg = await update.message.reply_text(f"Lade Zeitdaten fur {location}...")
    result = await get_time_for_location(location)
    await msg.edit_text(result, parse_mode=ParseMode.HTML)


# ─────────────────────────────────────────────
#  Admin: Ban / Unban / Kick
# ─────────────────────────────────────────────

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    uid, uname = await _get_target_user(update, context)
    if not uid:
        await update.message.reply_text(
            "Antworte auf eine Nachricht oder gib die User-ID an."
        )
        return
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "Kein Grund angegeben"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        msg = await update.message.reply_text(
            f"User <code>{uname}</code> (ID: <code>{uid}</code>) wurde gebannt.\n"
            f"Grund: {reason}",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        msg = await update.message.reply_text(f"Fehler: {e.message}")
    await asyncio.sleep(10)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    uid, uname = await _get_target_user(update, context)
    if not uid:
        await update.message.reply_text("Bitte User-ID angeben: /unban 123456")
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, uid, only_if_banned=True)
        msg = await update.message.reply_text(
            f"User <code>{uid}</code> wurde entbannt.",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        msg = await update.message.reply_text(f"Fehler: {e.message}")
    await asyncio.sleep(8)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    uid, uname = await _get_target_user(update, context)
    if not uid:
        await update.message.reply_text("Antworte auf eine Nachricht.")
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await context.bot.unban_chat_member(update.effective_chat.id, uid)
        msg = await update.message.reply_text(
            f"User <code>{uname}</code> wurde gekickt.",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        msg = await update.message.reply_text(f"Fehler: {e.message}")
    await asyncio.sleep(8)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────
#  Admin: Mute / Unmute
# ─────────────────────────────────────────────

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    uid, uname = await _get_target_user(update, context)
    if not uid:
        await update.message.reply_text("Antworte auf eine Nachricht.")
        return
    # Parse duration in minutes (default 60)
    minutes = 60
    args = context.args or []
    for arg in args:
        try:
            minutes = int(arg)
            break
        except ValueError:
            pass

    until = datetime.now().timestamp() + minutes * 60
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            uid,
            ChatPermissions(can_send_messages=False),
            until_date=int(until),
        )
        msg = await update.message.reply_text(
            f"User <code>{uname}</code> wurde fur <b>{minutes} Minuten</b> stummgeschaltet.",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        msg = await update.message.reply_text(f"Fehler: {e.message}")
    await asyncio.sleep(10)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    uid, uname = await _get_target_user(update, context)
    if not uid:
        await update.message.reply_text("Antworte auf eine Nachricht.")
        return
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            uid,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        msg = await update.message.reply_text(
            f"User <code>{uname}</code> kann wieder schreiben.",
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        msg = await update.message.reply_text(f"Fehler: {e.message}")
    await asyncio.sleep(8)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────
#  Admin: Warn / Unwarn / Warnings
# ─────────────────────────────────────────────

async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    uid, uname = await _get_target_user(update, context)
    if not uid:
        await update.message.reply_text("Antworte auf eine Nachricht.")
        return
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "Kein Grund"
    db.add_warning(uid, update.effective_chat.id, reason)
    count = db.get_warnings(uid)
    if count >= MAX_WARNINGS:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, uid)
            msg = await update.message.reply_text(
                f"User <code>{uname}</code> wurde nach {count} Verwarnungen <b>gebannt</b>.",
                parse_mode=ParseMode.HTML,
            )
        except BadRequest as e:
            msg = await update.message.reply_text(f"Gebannt (Fehler: {e.message})")
    else:
        remaining = MAX_WARNINGS - count
        msg = await update.message.reply_text(
            f"User <code>{uname}</code> verwarnt. ({count}/{MAX_WARNINGS})\n"
            f"Noch {remaining} Verwarnung(en) bis zum Ban.\n"
            f"Grund: {reason}",
            parse_mode=ParseMode.HTML,
        )
    await asyncio.sleep(10)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


async def cmd_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    uid, uname = await _get_target_user(update, context)
    if not uid:
        await update.message.reply_text("Antworte auf eine Nachricht.")
        return
    db.remove_last_warning(uid)
    count = db.get_warnings(uid)
    msg = await update.message.reply_text(
        f"Letzte Verwarnung von <code>{uname}</code> entfernt. ({count}/{MAX_WARNINGS})",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(8)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


async def cmd_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, uname = await _get_target_user(update, context)
    if not uid:
        uid = update.effective_user.id
        uname = update.effective_user.first_name
    count = db.get_warnings(uid)
    await update.message.reply_text(
        f"Verwarnungen fur <code>{uname}</code>: <b>{count}/{MAX_WARNINGS}</b>",
        parse_mode=ParseMode.HTML,
    )


# ─────────────────────────────────────────────
#  Admin: Pin / Unpin
# ─────────────────────────────────────────────

async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Antworte auf die Nachricht, die du pinnen mochtest.")
        return
    try:
        await context.bot.pin_chat_message(
            update.effective_chat.id,
            update.message.reply_to_message.message_id,
            disable_notification=False,
        )
        msg = await update.message.reply_text("Nachricht wurde gepinnt.")
    except BadRequest as e:
        msg = await update.message.reply_text(f"Fehler: {e.message}")
    await asyncio.sleep(5)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


async def cmd_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    try:
        await context.bot.unpin_all_chat_messages(update.effective_chat.id)
        msg = await update.message.reply_text("Alle Pins wurden entfernt.")
    except BadRequest as e:
        msg = await update.message.reply_text(f"Fehler: {e.message}")
    await asyncio.sleep(5)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────
#  Admin: Set Rules (ConversationHandler)
# ─────────────────────────────────────────────

async def cmd_setrules_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return ConversationHandler.END
    await update.message.reply_text(
        "Bitte sende jetzt die neuen Gruppenregeln (als eine Nachricht).\n"
        "Abbrechen mit /cancel"
    )
    return AWAITING_RULES


async def cmd_setrules_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = update.message.text
    set_group_rules(update.effective_chat.id, rules_text)
    await update.message.reply_text("Gruppenregeln wurden gespeichert.")
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  Admin: Set Welcome (ConversationHandler)
# ─────────────────────────────────────────────

async def cmd_setwelcome_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return ConversationHandler.END
    await update.message.reply_text(
        "Sende die neue Willkommensnachricht.\n"
        "Variablen: {name}, {id}, {chat}\n"
        "Abbrechen mit /cancel"
    )
    return AWAITING_WELCOME


async def cmd_setwelcome_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = update.message.text
    set_welcome_message(update.effective_chat.id, welcome_text)
    await update.message.reply_text("Willkommensnachricht gespeichert.")
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  Admin: Broadcast (ConversationHandler)
# ─────────────────────────────────────────────

async def cmd_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in BOT_ADMINS:
        await update.message.reply_text("Nur Bot-Admins konnen broadcast benutzen.")
        return ConversationHandler.END
    await update.message.reply_text(
        "Sende die Broadcast-Nachricht.\nAbbrechen mit /cancel"
    )
    return AWAITING_BROADCAST


async def cmd_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_ids = db.get_all_chats()
    sent, failed = 0, 0
    for cid in chat_ids:
        try:
            await context.bot.send_message(cid, text)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"Broadcast abgeschlossen.\nGesendet: {sent} | Fehler: {failed}"
    )
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Abgebrochen.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ─────────────────────────────────────────────
#  Whitelist management
# ─────────────────────────────────────────────

WHITELIST_MAPPING = {
    "frau": ("whitelistfemale", "Frauen-Whitelist"),
    "mann": ("whitelistmale", "Manner-Whitelist"),
    "sozialmedia": ("whitelistsozialmedia", "SozialMedia-Whitelist"),
    "parascha": ("whitelistparascha", "Parascha-Whitelist"),
    "info": ("whitelistinfo", "Info-Whitelist"),
}


async def cmd_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    if not context.args:
        await update.message.reply_text(
            "Verwendung: /whitelist [frau|mann|sozialmedia|parascha|info]\n"
            "Antworte dabei auf die Nachricht des Users."
        )
        return
    cat = context.args[0].lower()
    if cat not in WHITELIST_MAPPING:
        await update.message.reply_text(f"Unbekannte Kategorie: {cat}")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Antworte auf eine Nachricht des zu whitelistenden Users.")
        return
    target = update.message.reply_to_message.from_user
    table, label = WHITELIST_MAPPING[cat]
    db.save_list_to_table(table, [target.id])
    msg = await update.message.reply_text(
        f"{_mention(target)} zur {label} hinzugefugt.",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(8)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


async def cmd_remove_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _admin_check(update, context):
        return
    if not context.args:
        await update.message.reply_text(
            "Verwendung: /removefromwhitelist [frau|mann|sozialmedia|parascha|info]"
        )
        return
    cat = context.args[0].lower()
    if cat not in WHITELIST_MAPPING:
        await update.message.reply_text(f"Unbekannte Kategorie: {cat}")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Antworte auf eine Nachricht des Users.")
        return
    target = update.message.reply_to_message.from_user
    table, label = WHITELIST_MAPPING[cat]
    db.remove_from_list(table, target.id)
    msg = await update.message.reply_text(
        f"{_mention(target)} aus der {label} entfernt.",
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(8)
    try:
        await msg.delete()
        await update.message.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────
#  Inline Keyboard Callbacks
# ─────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    main_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Hilfe", callback_data="help"),
            InlineKeyboardButton("Info", callback_data="info"),
        ],
        [
            InlineKeyboardButton("Regeln", callback_data="rules"),
            InlineKeyboardButton("Standort", callback_data="request_location"),
        ],
        [InlineKeyboardButton("Admin Befehle", callback_data="admin_help")],
    ])

    if data == "main_menu":
        user = query.from_user
        await query.edit_message_text(
            f"Schalom {_mention(user)}!\n\nWahle eine Option.",
            reply_markup=main_keyboard,
            parse_mode=ParseMode.HTML,
        )

    elif data == "help":
        keyboard = [[InlineKeyboardButton("Hauptmenu", callback_data="main_menu")]]
        await query.edit_message_text(
            HELP_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )

    elif data == "admin_help":
        keyboard = [[InlineKeyboardButton("Hauptmenu", callback_data="main_menu")]]
        await query.edit_message_text(
            ADMIN_HELP_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )

    elif data == "rules":
        rules = get_group_rules(query.message.chat_id)
        if not rules:
            rules = "Noch keine Regeln gesetzt."
        keyboard = [[InlineKeyboardButton("Hauptmenu", callback_data="main_menu")]]
        await query.edit_message_text(
            f"<b>Gruppenregeln</b>\n\n{rules}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )

    elif data == "info":
        user = query.from_user
        warnings = db.get_warnings(user.id)
        username = f"@{user.username}" if user.username else "–"
        text = (
            f"<b>Deine Info</b>\n\n"
            f"<b>Name:</b> {user.first_name}\n"
            f"<b>Username:</b> {username}\n"
            f"<b>ID:</b> <code>{user.id}</code>\n"
            f"<b>Verwarnungen:</b> {warnings}/{MAX_WARNINGS}"
        )
        keyboard = [[InlineKeyboardButton("Hauptmenu", callback_data="main_menu")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )

    elif data == "request_location":
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("Standort teilen", request_location=True)]],
            one_time_keyboard=True,
            resize_keyboard=True,
        )
        await query.message.reply_text(
            "Bitte teile deinen Standort uber die Schaltflache unten.",
            reply_markup=keyboard,
        )


# ─────────────────────────────────────────────
#  General message handler (anti-spam / topic check)
# ─────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route non-command messages: location handled separately."""
    message = update.message
    if not message:
        return

    # Location messages are handled by the dedicated handler
    if message.location:
        await handle_location(update, context)
        return

    # Register chat in DB for broadcast / web dropdown
    db.register_chat(
        message.chat_id,
        title=message.chat.title or message.chat.first_name or "",
        chat_type=message.chat.type or "",
    )


# ─────────────────────────────────────────────
#  Bot command setup
# ─────────────────────────────────────────────

async def post_init(application: Application):
    # Start scheduler: check every 60 s for due messages
    application.job_queue.run_repeating(
        check_and_send_scheduled,
        interval=60,
        first=10,
        name="message_scheduler",
    )
    logger.info("Nachrichten-Scheduler gestartet (Intervall: 60s)")

    commands = [
        ("start", "Bot starten"),
        ("help", "Alle Befehle anzeigen"),
        ("id", "User-ID anzeigen"),
        ("info", "Benutzerinfo"),
        ("rules", "Gruppenregeln"),
        ("stats", "Gruppenstatistiken"),
        ("location", "Standort teilen"),
        ("weather", "Wetter abfragen"),
        ("time", "Ortszeit abfragen"),
        ("roll", "Wurfeln"),
        ("coinflip", "Munze werfen"),
        ("ban", "[Admin] User bannen"),
        ("unban", "[Admin] User entbannen"),
        ("kick", "[Admin] User kicken"),
        ("mute", "[Admin] User stummschalten"),
        ("unmute", "[Admin] User entstummen"),
        ("warn", "[Admin] User verwarnen"),
        ("unwarn", "[Admin] Verwarnung entfernen"),
        ("warnings", "Verwarnungen anzeigen"),
        ("pin", "[Admin] Nachricht pinnen"),
        ("unpin", "[Admin] Alle Pins entfernen"),
        ("setrules", "[Admin] Regeln setzen"),
        ("setwelcome", "[Admin] Willkommensnachricht setzen"),
        ("whitelist", "[Admin] User whitelisten"),
        ("removefromwhitelist", "[Admin] User entwhitelisten"),
    ]
    await application.bot.set_my_commands(commands)


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # Conversation: setrules
    setrules_conv = ConversationHandler(
        entry_points=[CommandHandler("setrules", cmd_setrules_start)],
        states={AWAITING_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_setrules_receive)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Conversation: setwelcome
    setwelcome_conv = ConversationHandler(
        entry_points=[CommandHandler("setwelcome", cmd_setwelcome_start)],
        states={AWAITING_WELCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_setwelcome_receive)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Conversation: broadcast
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", cmd_broadcast_start)],
        states={AWAITING_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_broadcast_send)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("roll", cmd_roll))
    app.add_handler(CommandHandler("coinflip", cmd_coinflip))

    # Location & weather
    app.add_handler(CommandHandler("location", cmd_location))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("time", cmd_time))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    # Admin commands
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("kick", cmd_kick))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("unwarn", cmd_unwarn))
    app.add_handler(CommandHandler("warnings", cmd_warnings))
    app.add_handler(CommandHandler("pin", cmd_pin))
    app.add_handler(CommandHandler("unpin", cmd_unpin))
    app.add_handler(CommandHandler("whitelist", cmd_whitelist))
    app.add_handler(CommandHandler("removefromwhitelist", cmd_remove_whitelist))

    # Conversations
    app.add_handler(setrules_conv)
    app.add_handler(setwelcome_conv)
    app.add_handler(broadcast_conv)

    # Inline buttons
    app.add_handler(CallbackQueryHandler(button_callback))

    # New/left members
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_left_member))

    # General messages
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    logger.info("Bot wird gestartet...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
