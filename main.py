import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
# This allows your GitHub Pages frontend to talk to your Render backend safely
CORS(app) 

# Set up Gemini AI (Make sure to add GEMINI_API_KEY in your Render Environment Variables)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# 🚀 UPDATE: Added the System Instruction here to make the AI fun and friendly!
model = genai.GenerativeModel(
    'gemini-1.5-flash',
    system_instruction=(
        "You are Johnny Tec, a super fun, friendly, and energetic AI developer assistant. "
        "Always speak in a positive, upbeat tone and use emojis naturally 😊🚀. "
        "When the user asks for code, always wrap it in proper markdown blocks. "
        "If the user sends a sad emoji or short message like 'Nothing', be chill, friendly, and supportive, "
        "but keep it brief and lighthearted, not like a therapist."
    )
)

DB_PATH = "database/johnny_tec.db"

def init_db():
    """Initializes the database using your exact schema"""
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Run your exact schema setup
    cursor.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            country TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    
    # Create a default user so we have a user_id to attach the chats to!
    cursor.execute("INSERT OR IGNORE INTO users (id, name, email) VALUES (1, 'Default Guest', 'guest@johnnytec.com')")
    
    conn.commit()
    conn.close()

# Initialize the database when the server starts
init_db()

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    data = request.json
    user_message = data.get("message")
    
    if not user_message:
        return jsonify({"reply": "Error: No message provided."}), 400

    try:
        # 1. Ask Gemini AI for the response
        response = model.generate_content(user_message)
        ai_reply = response.text

        # 2. SAVE TO YOUR SQLITE DATABASE! 🚀
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # We use user_id = 1 for now until you build a login system
        cursor.execute(
            "INSERT INTO conversations (user_id, user_message, ai_response) VALUES (?, ?, ?)",
            (1, user_message, ai_reply)
        )
        
        conn.commit()
        conn.close()

        # 3. Send the saved response back to your frontend
        return jsonify({"reply": ai_reply})

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"reply": "My backend is having trouble processing that request right now."}), 500

if __name__ == '__main__':
    # Runs the server on port 5000 (Render will assign its own port in production)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
