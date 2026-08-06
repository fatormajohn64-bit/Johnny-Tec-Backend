import sqlite3
import os

DB_PATH = "database/johnny_tec.db"


def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Creates every table Johnny Tec needs. Safe to call on every startup —
    CREATE TABLE IF NOT EXISTS won't touch data that's already there."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS developers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            bio TEXT,
            github_url TEXT,
            primary_stack TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            country TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Maps an anonymous browser session (sent from the frontend) to a
        -- user row, so each visitor gets their own history without a login.
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            memory_type TEXT,
            content TEXT NOT NULL,
            importance TEXT DEFAULT 'normal',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lesson_name TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_lessons_user ON lessons(user_id);
    """)

    cursor.execute(
        "INSERT OR IGNORE INTO users (id, name, email) VALUES (1, 'Default Guest', 'guest@johnnytec.com')"
    )

    # Seed the developer profiles. UNIQUE(username) + OR IGNORE means this
    # is safe to run on every startup without creating duplicates.
    cursor.executemany(
        """INSERT OR IGNORE INTO developers (name, username, role, bio, github_url, primary_stack)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (
                'John Fatoma',
                'johnny-tec-dev',
                'Founder & Lead Developer',
                'Creator of Johnny Tec AI ecosystem.',
                'https://github.com/johnny-tec-dev',
                'Python, SQL, AI Architectures'
            ),
            (
                'Invisible 911',
                'invisible-911',
                'Developer Alias',
                'Secondary developer profile and system alias.',
                'https://github.com/invisible-911',
                'Database Engineering & Security'
            ),
        ]
    )

    conn.commit()
    conn.close()


def get_or_create_user_id(session_id: str) -> int:
    """Looks up which user a browser session belongs to, creating a new
    guest user + session mapping the first time we see that session_id."""
    if not session_id:
        return 1  # fallback to the shared default guest

    conn = get_db_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT user_id FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()

    if row:
        user_id = row["user_id"]
    else:
        cursor.execute(
            "INSERT INTO users (name, email, country) VALUES (?, NULL, NULL)",
            (f"Guest-{session_id[:8]}",)
        )
        user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id) VALUES (?, ?)",
            (session_id, user_id)
        )
        conn.commit()

    conn.close()
    return user_id


def save_conversation(user_id: int, user_message: str, ai_response: str):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO conversations (user_id, user_message, ai_response) VALUES (?, ?, ?)",
        (user_id, user_message, ai_response)
    )
    conn.commit()
    conn.close()


def get_recent_conversations(user_id: int, limit: int = 10):
    """Last N turns for this user, oldest first — this is what gives
    Johnny Tec short-term memory of the conversation."""
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT user_message, ai_response FROM conversations
           WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return list(reversed(rows))


def get_recent_activity(limit: int = 50):
    """Fetches recent interactions across all users for the /logs endpoint."""
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT 
            c.id,
            c.user_id,
            u.name AS user_name,
            c.user_message,
            c.ai_response,
            c.created_at
           FROM conversations c
           LEFT JOIN users u ON c.user_id = u.id
           ORDER BY c.id DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_memories(user_id: int):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT memory_type, content FROM memories WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    conn.close()
    return [f"{row['memory_type']}: {row['content']}" for row in rows]


def save_memory(user_id: int, memory_type: str, content: str, importance: str = "normal"):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO memories (user_id, memory_type, content, importance) VALUES (?, ?, ?)",
        (user_id, memory_type, content, importance)
    )
    conn.commit()
    conn.close()
