import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

import db_connector as db

app = Flask(__name__)
CORS(app)  # lets your GitHub Pages frontend talk to this Render backend

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_INSTRUCTION = (
    "You are Johnny Tec, a super fun, friendly, and energetic AI developer assistant. "
    "Talk like a real person texting a friend who's good at tech — warm and natural, "
    "never robotic or scripted. "
    "Use emojis naturally when they add feeling, but don't stuff every sentence with them. "
    "If the user's message has typos, bad grammar, or shorthand, silently understand what "
    "they meant and respond to that — never point out or correct their spelling unless "
    "they specifically ask. "
    "When the user asks for code, wrap it in proper markdown code blocks. "
    "If the user sends something short and low-energy like 'nothing' or a sad emoji, be "
    "chill, supportive, and brief — like a good friend checking in, not a therapist. "
    "Never repeat the user's message back to them or say things like 'Got it, I processed "
    "your message' — just respond the way ChatGPT or Claude would: naturally, to the point."
)

# NOTE: Google renames/retires Gemini models periodically. If this 404s,
# check https://ai.google.dev/gemini-api/docs/models for the current name.
model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=SYSTEM_INSTRUCTION)

db.init_db()


@app.route('/')
def home():
    return "✅ Johnny Tec AI backend is running."


@app.route('/chat', methods=['POST'])
def chat_endpoint():
    data = request.json or {}
    user_message = data.get("message")
    session_id = data.get("sessionId")

    if not user_message or not user_message.strip():
        return jsonify({"reply": "Error: No message provided."}), 400

    try:
        user_id = db.get_or_create_user_id(session_id)

        # Feed Gemini the last few turns so it actually remembers the
        # conversation instead of treating every message as brand new.
        history_rows = db.get_recent_conversations(user_id, limit=10)
        gemini_history = []
        for row in history_rows:
            gemini_history.append({"role": "user", "parts": [row["user_message"]]})
            gemini_history.append({"role": "model", "parts": [row["ai_response"]]})

        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(user_message)
        ai_reply = response.text

        db.save_conversation(user_id, user_message, ai_reply)

        return jsonify({"reply": ai_reply})

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"reply": "My backend is having trouble processing that request right now."}), 500


@app.route('/chat/<session_id>', methods=['DELETE'])
def clear_chat(session_id):
    """Wire this up to a 'New chat' button to wipe one visitor's history."""
    user_id = db.get_or_create_user_id(session_id)
    conn = db.get_db_connection()
    conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"cleared": True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
