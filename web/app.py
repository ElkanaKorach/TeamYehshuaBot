"""
TeamYehshua Bot — Web Interface (Flask)
Läuft parallel zum Telegram-Bot (via run.py).
"""

import json
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from database.db_operations import DatabaseManager

# ─────────────────────────────────────────────
#  App setup
# ─────────────────────────────────────────────

app = Flask(__name__)

# Configs aus configs/config.py laden
try:
    from configs.config import WEB_PASSWORD, WEB_SECRET_KEY, WEB_PORT
except ImportError:
    WEB_PASSWORD   = "admin"
    WEB_SECRET_KEY = "change-me-in-production"
    WEB_PORT       = 5000

app.secret_key = WEB_SECRET_KEY

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "mov", "avi",
                      "mp3", "ogg", "pdf", "zip", "docx", "txt"}

db = DatabaseManager()

WHITELIST_CATEGORIES = {
    "frau":        ("whitelistfemale",      "Frauen"),
    "mann":        ("whitelistmale",        "Männer"),
    "sozialmedia": ("whitelistsozialmedia", "Social Media"),
    "parascha":    ("whitelistparascha",    "Parascha"),
    "info":        ("whitelistinfo",        "Info"),
}

MSG_TYPES = ["text", "photo", "video", "document", "audio"]

# ─────────────────────────────────────────────
#  Auth
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─────────────────────────────────────────────
#  Auth routes
# ─────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == WEB_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Falsches Passwort.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────────
#  Dashboard
# ─────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    stats    = db.get_stats()
    recent   = db.get_scheduled_messages()[:10]
    chats    = db.get_all_chats()
    warnings = db.get_all_warnings()[:5]
    return render_template(
        "dashboard.html",
        stats=stats,
        recent=recent,
        chats=chats,
        warnings=warnings,
    )


# ─────────────────────────────────────────────
#  Scheduled Messages
# ─────────────────────────────────────────────

@app.route("/messages")
@login_required
def messages():
    status_filter = request.args.get("status", "")
    msgs  = db.get_scheduled_messages(status=status_filter or None)
    chats = {c["chat_id"]: c["title"] or str(c["chat_id"]) for c in db.get_all_chats()}
    return render_template(
        "messages.html",
        messages=msgs,
        chats=chats,
        status_filter=status_filter,
    )


@app.route("/messages/add", methods=["GET", "POST"])
@login_required
def add_message():
    chats = db.get_all_chats()

    if request.method == "POST":
        chat_id      = request.form.get("chat_id", "").strip()
        msg_type     = request.form.get("message_type", "text")
        content      = request.form.get("content", "").strip()
        caption      = request.form.get("caption", "").strip()
        media_url    = request.form.get("media_url", "").strip()
        media_file_id = request.form.get("media_file_id", "").strip()
        scheduled_at = request.form.get("scheduled_at", "").strip()
        buttons_raw  = request.form.get("buttons_json", "").strip()

        # Validation
        if not chat_id:
            flash("Bitte Chat-ID angeben.", "danger")
            return render_template("add_message.html", chats=chats, msg_types=MSG_TYPES)
        if not scheduled_at:
            flash("Bitte Datum/Uhrzeit angeben.", "danger")
            return render_template("add_message.html", chats=chats, msg_types=MSG_TYPES)
        if msg_type == "text" and not content:
            flash("Text darf nicht leer sein.", "danger")
            return render_template("add_message.html", chats=chats, msg_types=MSG_TYPES)

        # Normalize datetime to ISO format YYYY-MM-DDTHH:MM
        try:
            dt = datetime.fromisoformat(scheduled_at.replace(" ", "T")[:16])
            scheduled_at = dt.strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Ungültiges Datumsformat.", "danger")
            return render_template("add_message.html", chats=chats, msg_types=MSG_TYPES)

        # Validate/normalize buttons JSON
        buttons_json = None
        if buttons_raw:
            try:
                parsed = json.loads(buttons_raw)
                buttons_json = json.dumps(parsed)
            except json.JSONDecodeError:
                flash("Ungültiges Button-JSON.", "danger")
                return render_template("add_message.html", chats=chats, msg_types=MSG_TYPES)

        # Handle file upload
        media_local_path = None
        uploaded = request.files.get("media_file")
        if uploaded and uploaded.filename:
            if not allowed_file(uploaded.filename):
                flash("Dateiformat nicht erlaubt.", "danger")
                return render_template("add_message.html", chats=chats, msg_types=MSG_TYPES)
            fname = secure_filename(uploaded.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
            uploaded.save(save_path)
            media_local_path = save_path

        msg_id = db.add_scheduled_message(
            chat_id          = int(chat_id),
            message_type     = msg_type,
            scheduled_at     = scheduled_at,
            content          = content or None,
            caption          = caption or None,
            media_url        = media_url or None,
            media_file_id    = media_file_id or None,
            media_local_path = media_local_path,
            buttons_json     = buttons_json,
        )

        # Register chat so it shows in dropdowns
        db.register_chat(int(chat_id), chat_id)

        flash(f"Nachricht #{msg_id} geplant für {scheduled_at}.", "success")
        return redirect(url_for("messages"))

    return render_template("add_message.html", chats=chats, msg_types=MSG_TYPES)


@app.route("/messages/<int:msg_id>/cancel", methods=["POST"])
@login_required
def cancel_message(msg_id):
    db.cancel_scheduled_message(msg_id)
    flash(f"Nachricht #{msg_id} abgebrochen.", "warning")
    return redirect(url_for("messages"))


@app.route("/messages/<int:msg_id>/delete", methods=["POST"])
@login_required
def delete_message(msg_id):
    db.delete_scheduled_message(msg_id)
    flash(f"Nachricht #{msg_id} gelöscht.", "danger")
    return redirect(url_for("messages"))


@app.route("/messages/<int:msg_id>")
@login_required
def view_message(msg_id):
    msg = db.get_scheduled_message(msg_id)
    if not msg:
        flash("Nachricht nicht gefunden.", "danger")
        return redirect(url_for("messages"))
    return render_template("view_message.html", msg=msg)


# ─────────────────────────────────────────────
#  Settings
# ─────────────────────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    chats = db.get_all_chats()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_rules":
            chat_id = request.form.get("chat_id")
            rules   = request.form.get("rules", "")
            if chat_id:
                db.set_setting(int(chat_id), "rules", rules)
                flash("Regeln gespeichert.", "success")

        elif action == "save_welcome":
            chat_id  = request.form.get("chat_id")
            welcome  = request.form.get("welcome", "")
            if chat_id:
                db.set_setting(int(chat_id), "welcome", welcome)
                flash("Willkommensnachricht gespeichert.", "success")

        return redirect(url_for("settings"))

    # Build per-chat settings for display
    chat_settings = []
    for chat in chats:
        cid = chat["chat_id"]
        chat_settings.append({
            "chat":    chat,
            "rules":   db.get_setting(cid, "rules"),
            "welcome": db.get_setting(cid, "welcome"),
        })

    return render_template("settings.html", chat_settings=chat_settings, chats=chats)


# ─────────────────────────────────────────────
#  Whitelist
# ─────────────────────────────────────────────

@app.route("/whitelist")
@login_required
def whitelist():
    data = {}
    for cat, (table, label) in WHITELIST_CATEGORIES.items():
        data[cat] = {
            "label":   label,
            "members": db.get_list(table),
        }
    return render_template("whitelist.html", data=data, categories=WHITELIST_CATEGORIES)


@app.route("/whitelist/add", methods=["POST"])
@login_required
def whitelist_add():
    cat     = request.form.get("category", "").lower()
    user_id = request.form.get("user_id", "").strip()
    if cat not in WHITELIST_CATEGORIES:
        flash("Unbekannte Kategorie.", "danger")
        return redirect(url_for("whitelist"))
    try:
        uid = int(user_id)
    except ValueError:
        flash("Ungültige User-ID.", "danger")
        return redirect(url_for("whitelist"))
    table, label = WHITELIST_CATEGORIES[cat]
    db.save_list_to_table(table, [uid])
    flash(f"User {uid} zur {label}-Whitelist hinzugefügt.", "success")
    return redirect(url_for("whitelist"))


@app.route("/whitelist/remove", methods=["POST"])
@login_required
def whitelist_remove():
    cat     = request.form.get("category", "").lower()
    user_id = request.form.get("user_id", "").strip()
    if cat not in WHITELIST_CATEGORIES:
        flash("Unbekannte Kategorie.", "danger")
        return redirect(url_for("whitelist"))
    try:
        uid = int(user_id)
    except ValueError:
        flash("Ungültige User-ID.", "danger")
        return redirect(url_for("whitelist"))
    table, label = WHITELIST_CATEGORIES[cat]
    db.remove_from_list(table, uid)
    flash(f"User {uid} aus der {label}-Whitelist entfernt.", "warning")
    return redirect(url_for("whitelist"))


# ─────────────────────────────────────────────
#  Warnings
# ─────────────────────────────────────────────

@app.route("/warnings")
@login_required
def warnings_page():
    all_warns = db.get_all_warnings()
    return render_template("warnings.html", warnings=all_warns)


@app.route("/warnings/reset", methods=["POST"])
@login_required
def reset_warnings():
    user_id = request.form.get("user_id", "").strip()
    try:
        db.reset_warnings(int(user_id))
        flash(f"Verwarnungen für User {user_id} zurückgesetzt.", "success")
    except ValueError:
        flash("Ungültige User-ID.", "danger")
    return redirect(url_for("warnings_page"))


# ─────────────────────────────────────────────
#  API (JSON) — for fetch() calls from JS
# ─────────────────────────────────────────────

@app.route("/api/stats")
@login_required
def api_stats():
    from flask import jsonify
    return jsonify(db.get_stats())


# ─────────────────────────────────────────────
#  Template helpers
# ─────────────────────────────────────────────

@app.template_filter("dt_format")
def dt_format(value):
    if not value:
        return "–"
    try:
        dt = datetime.fromisoformat(str(value)[:16])
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(value)


@app.template_filter("status_badge")
def status_badge(status):
    badges = {
        "pending":   "warning",
        "sent":      "success",
        "failed":    "danger",
        "cancelled": "secondary",
    }
    color = badges.get(status, "light")
    label = {
        "pending":   "Ausstehend",
        "sent":      "Gesendet",
        "failed":    "Fehler",
        "cancelled": "Abgebrochen",
    }.get(status, status)
    return f'<span class="badge bg-{color}">{label}</span>'


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=WEB_PORT, debug=True)
