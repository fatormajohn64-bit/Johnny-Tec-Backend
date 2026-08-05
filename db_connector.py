import sqlite3
import os

# Updated to save inside the 'database' folder shown in your repo
DB_PATH = "database/johnny_tec.db"

def get_db_connection():
    # Ensure the directory exists before connecting
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    
    cursor = conn.cursor()
    
    # Auto-create tables using the FULL Johnny Tec v1.0 Schema
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS developers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            country TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

        -- Indexes for high-speed queries
        CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_lessons_user ON lessons(user_id);
    """)
    
    # Create a default guest user. 
    # Since foreign keys are ON, you cannot save a conversation without a valid user_id!
    cursor.execute("INSERT OR IGNORE INTO users (id, name, email) VALUES (1, 'Guest User', 'guest@johnnytec.com')")
    
    conn.commit()
    return conn

def save_conversation(user_id: int, user_message: str, ai_response: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (user_id, user_message, ai_response) VALUES (?, ?, ?)",
        (user_id, user_message, ai_response)
    )
    conn.commit()
    conn.close()

def get_user_memories(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT memory_type, content FROM memories WHERE user_id = ?", 
        (user_id,)
    ).fetchall()
    conn.close()
    return [f"{row['memory_type']}: {row['content']}" for row in rows]
    
