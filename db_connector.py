import sqlite3
import os

DB_PATH = "../johnny-tec-database/database/johnny_tec.db"

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
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
  
