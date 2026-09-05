import sqlite3
from pathlib import Path
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "mailtowhatsapp.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            gmail_token TEXT,
            whatsapp_number TEXT,
            monitoring_enabled INTEGER DEFAULT 0,
            last_checked_at TIMESTAMP,
            emails_sent_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Safe migrations for databases created with older versions.
    cursor.execute("PRAGMA table_info(users)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "monitoring_enabled" not in columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN monitoring_enabled INTEGER DEFAULT 0
        """)

    if "last_checked_at" not in columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN last_checked_at TIMESTAMP
        """)

    if "emails_sent_count" not in columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN emails_sent_count INTEGER DEFAULT 0
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            gmail_message_id TEXT NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, gmail_message_id),
            FOREIGN KEY(user_id)
            REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


def create_user(email):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:
        user_id = existing_user["id"]
    else:
        cursor.execute(
            "INSERT INTO users (email) VALUES (?)",
            (email,)
        )
        connection.commit()
        user_id = cursor.lastrowid

    connection.close()
    return user_id


def get_user(email):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )

    user = cursor.fetchone()

    connection.close()
    return user


def get_user_by_id(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    connection.close()
    return user


def save_gmail_token(email, token):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET gmail_token = ?
        WHERE email = ?
    """, (token, email))

    connection.commit()
    connection.close()


def save_whatsapp_number(email, whatsapp_number):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET whatsapp_number = ?
        WHERE email = ?
    """, (whatsapp_number, email))

    connection.commit()
    connection.close()


def set_monitoring_enabled(user_id, enabled):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET monitoring_enabled = ?
        WHERE id = ?
    """, (
        1 if enabled else 0,
        user_id
    ))

    connection.commit()
    connection.close()


def is_monitoring_enabled(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT monitoring_enabled
        FROM users
        WHERE id = ?
    """, (user_id,))

    result = cursor.fetchone()

    connection.close()

    if result is None:
        return False

    return bool(result["monitoring_enabled"])


def update_last_checked(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
        UPDATE users
        SET last_checked_at = ?
        WHERE id = ?
    """, (now, user_id))

    connection.commit()
    connection.close()


def increment_sent_count(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET emails_sent_count =
            COALESCE(emails_sent_count, 0) + 1
        WHERE id = ?
    """, (user_id,))

    connection.commit()
    connection.close()


def is_email_processed(user_id, gmail_message_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM processed_emails
        WHERE user_id = ?
        AND gmail_message_id = ?
    """, (
        user_id,
        gmail_message_id
    ))

    result = cursor.fetchone()

    connection.close()

    return result is not None


def mark_email_processed(user_id, gmail_message_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO processed_emails (
            user_id,
            gmail_message_id
        )
        VALUES (?, ?)
    """, (
        user_id,
        gmail_message_id
    ))

    connection.commit()
    connection.close()


def get_dashboard_stats(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            emails_sent_count,
            last_checked_at
        FROM users
        WHERE id = ?
    """, (user_id,))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) AS processed_count
        FROM processed_emails
        WHERE user_id = ?
    """, (user_id,))

    processed = cursor.fetchone()

    connection.close()

    if user is None:
        return None

    return {
        "emails_sent": user["emails_sent_count"] or 0,
        "processed_emails": processed["processed_count"] or 0,
        "last_checked_at": user["last_checked_at"]
    }


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully! ✅")
    