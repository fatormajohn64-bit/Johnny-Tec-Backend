import sqlite3
import os

DB_PATH = "johnny_tec.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Auto-create tables on server start if they don't exist
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_message TEXT,
            ai_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            memory_type TEXT,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
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
    
