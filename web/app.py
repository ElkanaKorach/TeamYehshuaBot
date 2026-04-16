"""
Nazarener Bot — Web Interface (Flask)
Läuft parallel zum Telegram-Bot (via run.py).
"""

import json
import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    Markup,
    flash,
    jsonify,
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

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp",
    "mp4", "mov", "avi", "mkv",
    "mp3", "ogg", "m4a",
    "pdf", "zip", "docx", "txt",
}

db = DatabaseManager()


MSG_TYPES = ["text", "photo", "video", "document", "audio"]

REPEAT_OPTIONS = [
    ("none",    "Einmalig"),
    ("daily",   "Täglich"),
    ("weekly",  "Wöchentlich"),
    ("monthly", "Monatlich"),
]

# ─────────────────────────────────────────────
#  Context processor — injects `now` into every template
# ─────────────────────────────────────────────

@app.context_processor
def inject_globals():
    return {"now": datetime.now().strftime("%d.%m.%Y %H:%M")}


# ─────────────────────────────────────────────
#  Auth helpers
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
#  Scheduled Messages — list
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


# ─────────────────────────────────────────────
#  Shared helper: build message from form
# ─────────────────────────────────────────────

def _parse_message_form():
    """Parse the add/edit form. Returns (data_dict, error_string or None)."""
    chat_id       = request.form.get("chat_id", "").strip()
    msg_type      = request.form.get("message_type", "text")
    content       = request.form.get("content", "").strip()
    caption       = request.form.get("caption", "").strip()
    media_url     = request.form.get("media_url", "").strip()
    media_file_id = request.form.get("media_file_id", "").strip()
    scheduled_at  = request.form.get("scheduled_at", "").strip()
    buttons_raw   = request.form.get("buttons_json", "").strip()
    repeat        = request.form.get("repeat", "none")

    if not chat_id:
        return None, "Bitte Chat-ID angeben."
    if not scheduled_at:
        return None, "Bitte Datum/Uhrzeit angeben."
    if msg_type == "text" and not content:
        return None, "Text darf nicht leer sein."

    # Normalise datetime
    try:
        dt = datetime.fromisoformat(scheduled_at.replace(" ", "T")[:16])
        scheduled_at = dt.strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return None, "Ungültiges Datumsformat (YYYY-MM-DDTHH:MM erwartet)."

    # Validate buttons JSON
    buttons_json = None
    if buttons_raw:
        try:
            parsed = json.loads(buttons_raw)
            buttons_json = json.dumps(parsed)
        except json.JSONDecodeError:
            return None, "Ungültiges Button-JSON."

    # Handle file upload
    media_local_path = None
    uploaded = request.files.get("media_file")
    if uploaded and uploaded.filename:
        if not allowed_file(uploaded.filename):
            return None, "Dateiformat nicht erlaubt."
        fname = secure_filename(uploaded.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
        uploaded.save(save_path)
        media_local_path = save_path

    return {
        "chat_id":          int(chat_id),
        "message_type":     msg_type,
        "content":          content or None,
        "caption":          caption or None,
        "media_url":        media_url or None,
        "media_file_id":    media_file_id or None,
        "media_local_path": media_local_path,
        "buttons_json":     buttons_json,
        "scheduled_at":     scheduled_at,
        "repeat":           repeat if repeat in ("none", "daily", "weekly", "monthly") else "none",
    }, None


# ─────────────────────────────────────────────
#  Add Message
# ─────────────────────────────────────────────

@app.route("/messages/add", methods=["GET", "POST"])
@login_required
def add_message():
    chats     = db.get_all_chats()
    templates = db.get_templates()

    if request.method == "POST":
        data, err = _parse_message_form()
        if err:
            flash(err, "danger")
            return render_template(
                "add_message.html", chats=chats, msg_types=MSG_TYPES,
                repeat_options=REPEAT_OPTIONS, templates=templates,
            )

        msg_id = db.add_scheduled_message(**data)
        db.register_chat(data["chat_id"])
        flash(f"Nachricht #{msg_id} geplant für {data['scheduled_at']}.", "success")
        return redirect(url_for("messages"))

    # Pre-fill from template if ?tpl=ID
    prefill = {}
    tpl_id = request.args.get("tpl")
    if tpl_id:
        tpl = db.get_template(int(tpl_id))
        if tpl:
            prefill = tpl

    return render_template(
        "add_message.html",
        chats=chats,
        msg_types=MSG_TYPES,
        repeat_options=REPEAT_OPTIONS,
        templates=templates,
        prefill=prefill,
    )


# ─────────────────────────────────────────────
#  Edit Message
# ─────────────────────────────────────────────

@app.route("/messages/<int:msg_id>/edit", methods=["GET", "POST"])
@login_required
def edit_message(msg_id):
    msg = db.get_scheduled_message(msg_id)
    if not msg:
        flash("Nachricht nicht gefunden.", "danger")
        return redirect(url_for("messages"))
    if msg["status"] != "pending":
        flash("Nur ausstehende Nachrichten können bearbeitet werden.", "warning")
        return redirect(url_for("view_message", msg_id=msg_id))

    chats = db.get_all_chats()

    if request.method == "POST":
        data, err = _parse_message_form()
        if err:
            flash(err, "danger")
            return render_template(
                "edit_message.html", msg=msg, chats=chats,
                msg_types=MSG_TYPES, repeat_options=REPEAT_OPTIONS,
            )
        db.update_scheduled_message(
            msg_id=msg_id,
            chat_id=data["chat_id"],
            message_type=data["message_type"],
            scheduled_at=data["scheduled_at"],
            content=data["content"],
            caption=data["caption"],
            media_url=data["media_url"],
            media_file_id=data["media_file_id"],
            buttons_json=data["buttons_json"],
            repeat=data["repeat"],
        )
        flash(f"Nachricht #{msg_id} aktualisiert.", "success")
        return redirect(url_for("view_message", msg_id=msg_id))

    return render_template(
        "edit_message.html",
        msg=msg,
        chats=chats,
        msg_types=MSG_TYPES,
        repeat_options=REPEAT_OPTIONS,
    )


# ─────────────────────────────────────────────
#  Duplicate Message
# ─────────────────────────────────────────────

@app.route("/messages/<int:msg_id>/duplicate", methods=["POST"])
@login_required
def duplicate_message(msg_id):
    msg = db.get_scheduled_message(msg_id)
    if not msg:
        flash("Nachricht nicht gefunden.", "danger")
        return redirect(url_for("messages"))
    new_id = db.add_scheduled_message(
        chat_id          = msg["chat_id"],
        message_type     = msg["message_type"],
        scheduled_at     = msg["scheduled_at"],
        content          = msg["content"],
        caption          = msg["caption"],
        media_url        = msg["media_url"],
        media_file_id    = msg["media_file_id"],
        media_local_path = msg["media_local_path"],
        buttons_json     = msg["buttons_json"],
        repeat           = msg.get("repeat", "none"),
    )
    flash(f"Nachricht #{msg_id} als #{new_id} dupliziert. Bitte Zeitpunkt anpassen.", "info")
    return redirect(url_for("edit_message", msg_id=new_id))


# ─────────────────────────────────────────────
#  View / Cancel / Delete Message
# ─────────────────────────────────────────────

@app.route("/messages/<int:msg_id>")
@login_required
def view_message(msg_id):
    msg = db.get_scheduled_message(msg_id)
    if not msg:
        flash("Nachricht nicht gefunden.", "danger")
        return redirect(url_for("messages"))
    return render_template("view_message.html", msg=msg, repeat_options=dict(REPEAT_OPTIONS))


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


# ─────────────────────────────────────────────
#  Templates
# ─────────────────────────────────────────────

@app.route("/templates")
@login_required
def templates_page():
    templates = db.get_templates()
    return render_template("templates.html", templates=templates, msg_types=MSG_TYPES)


@app.route("/templates/add", methods=["POST"])
@login_required
def template_add():
    name         = request.form.get("name", "").strip()
    msg_type     = request.form.get("message_type", "text")
    content      = request.form.get("content", "").strip()
    caption      = request.form.get("caption", "").strip()
    buttons_raw  = request.form.get("buttons_json", "").strip()

    if not name:
        flash("Name darf nicht leer sein.", "danger")
        return redirect(url_for("templates_page"))

    buttons_json = None
    if buttons_raw:
        try:
            buttons_json = json.dumps(json.loads(buttons_raw))
        except json.JSONDecodeError:
            flash("Ungültiges Button-JSON.", "danger")
            return redirect(url_for("templates_page"))

    db.add_template(
        name=name,
        message_type=msg_type,
        content=content or None,
        caption=caption or None,
        buttons_json=buttons_json,
    )
    flash(f"Vorlage '{name}' gespeichert.", "success")
    return redirect(url_for("templates_page"))


@app.route("/templates/<int:tpl_id>/delete", methods=["POST"])
@login_required
def template_delete(tpl_id):
    db.delete_template(tpl_id)
    flash("Vorlage gelöscht.", "warning")
    return redirect(url_for("templates_page"))


@app.route("/api/templates/<int:tpl_id>")
@login_required
def api_template(tpl_id):
    tpl = db.get_template(tpl_id)
    if not tpl:
        return jsonify({}), 404
    return jsonify(tpl)


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
            if chat_id:
                db.set_setting(int(chat_id), "rules", request.form.get("rules", ""))
                flash("Regeln gespeichert.", "success")
        elif action == "save_welcome":
            chat_id = request.form.get("chat_id")
            if chat_id:
                db.set_setting(int(chat_id), "welcome", request.form.get("welcome", ""))
                flash("Willkommensnachricht gespeichert.", "success")
        elif action == "add_chat":
            chat_id = request.form.get("chat_id", "").strip()
            try:
                db.register_chat(int(chat_id))
                flash(f"Chat {chat_id} hinzugefügt.", "success")
            except ValueError:
                flash("Ungültige Chat-ID.", "danger")
        return redirect(url_for("settings"))

    chat_settings = [
        {
            "chat":    c,
            "rules":   db.get_setting(c["chat_id"], "rules"),
            "welcome": db.get_setting(c["chat_id"], "welcome"),
        }
        for c in chats
    ]
    return render_template("settings.html", chat_settings=chat_settings, chats=chats)


# ─────────────────────────────────────────────
#  Whitelist
# ─────────────────────────────────────────────

@app.route("/whitelist")
@login_required
def whitelist():
    members = db.get_whitelist()
    return render_template("whitelist.html", members=members)


@app.route("/whitelist/add", methods=["POST"])
@login_required
def whitelist_add():
    user_id = request.form.get("user_id", "").strip()
    try:
        uid = int(user_id)
    except ValueError:
        flash("Ungültige User-ID.", "danger")
        return redirect(url_for("whitelist"))
    db.add_to_whitelist(uid)
    flash(f"User {uid} zur Whitelist hinzugefügt.", "success")
    return redirect(url_for("whitelist"))


@app.route("/whitelist/remove", methods=["POST"])
@login_required
def whitelist_remove():
    user_id = request.form.get("user_id", "").strip()
    try:
        uid = int(user_id)
    except ValueError:
        flash("Ungültige User-ID.", "danger")
        return redirect(url_for("whitelist"))
    db.remove_from_whitelist(uid)
    flash(f"User {uid} aus der Whitelist entfernt.", "warning")
    return redirect(url_for("whitelist"))


# ─────────────────────────────────────────────
#  Warnings
# ─────────────────────────────────────────────

@app.route("/warnings")
@login_required
def warnings_page():
    return render_template("warnings.html", warnings=db.get_all_warnings())


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
#  JSON API
# ─────────────────────────────────────────────

@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify(db.get_stats())


# ─────────────────────────────────────────────
#  Template filters
# ─────────────────────────────────────────────

@app.template_filter("dt_format")
def dt_format(value):
    if not value:
        return "–"
    try:
        return datetime.fromisoformat(str(value)[:16]).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(value)


@app.template_filter("status_badge")
def status_badge(status):
    colors = {"pending": "warning", "sent": "success",
               "failed": "danger",  "cancelled": "secondary"}
    labels = {"pending": "Ausstehend", "sent": "Gesendet",
               "failed": "Fehler",     "cancelled": "Abgebrochen"}
    c = colors.get(status, "light")
    l = labels.get(status, status)
    return Markup(f'<span class="badge bg-{c}">{l}</span>')


@app.template_filter("repeat_label")
def repeat_label(value):
    labels = {"none": "Einmalig", "daily": "Täglich",
               "weekly": "Wöchentlich", "monthly": "Monatlich"}
    return labels.get(value, value or "Einmalig")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=WEB_PORT, debug=True)
