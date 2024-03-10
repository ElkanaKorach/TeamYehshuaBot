from database.warning_operations import load_warned_users_from_db

def load_warned_users():
    global warned_users
    warned_users = load_warned_users_from_db()
    print(f"Geladene {len(warned_users)} verwarnte Nutzer.")