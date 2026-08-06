import os
import hmac
from datetime import datetime
from html import escape
from flask import Flask, request, jsonify, Response
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

# Tracks the most recent /chat error so the home page can surface it
# instead of you having to dig through Render's logs.
last_error = None
last_error_time = None



PAGE_STYLE = """
<style>
    body {
        background: #0d0d14;
        color: #e6e6f0;
        font-family: -apple-system, Segoe UI, Roboto, sans-serif;
        margin: 0;
        padding: 24px 16px 60px;
    }
    h1 {
        background: linear-gradient(90deg, #6ea8fe, #b388ff);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        font-size: 1.6rem;
        margin-bottom: 4px;
    }
    .subtitle { color: #8a8aa3; margin-top: 0; margin-bottom: 24px; font-size: 0.9rem; }
    .card {
        background: #15151f;
        border: 1px solid #26263a;
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }
    .status-row { display: flex; align-items: center; gap: 8px; font-size: 0.95rem; margin-bottom: 6px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    .dot.ok { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
    .dot.err { background: #f87171; box-shadow: 0 0 6px #f87171; }
    a { color: #6ea8fe; }
    code { background: #1e1e2b; padding: 2px 6px; border-radius: 4px; font-size: 0.85rem; }
    .error-box {
        background: #2a1414;
        border: 1px solid #6b2b2b;
        border-radius: 12px;
        padding: 14px 16px;
        color: #ffb4b4;
        font-size: 0.9rem;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
</style>
"""


@app.route('/')
def home():
    if last_error:
        error_html = f"""
        <div class="card">
            <div class="status-row"><span class="dot err"></span> Last /chat error</div>
            <div class="error-box">[{escape(str(last_error_time))}]
{escape(str(last_error))}</div>
        </div>
        """
    else:
        error_html = """
        <div class="card">
            <div class="status-row"><span class="dot ok"></span> No errors logged yet</div>
        </div>
        """

    page = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Johnny Tec Backend</title>
        {PAGE_STYLE}
    </head>
    <body>
        <h1>Johnny Tec Backend</h1>
        <p class="subtitle">AI Architecture &amp; Database Operations Center</p>

        <div class="card">
            <div class="status-row"><span class="dot ok"></span> Server is running</div>
            <div class="status-row"><span class="dot ok"></span> Database connected</div>
        </div>

        {error_html}

        <div class="card">
            <p><strong>Endpoints</strong></p>
            <p><code>POST /chat</code> — send a message, get Johnny's reply</p>
            <p><code>GET /health</code> — health check</p>
            <p><a href="/logs">/logs</a> — live conversation log viewer</p>
        </div>
    </body>
    </html>
    """
    return Response(page, mimetype="text/html")


@app.route('/health')
def health():
    return jsonify({"status": "ok"})


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
        global last_error, last_error_time
        last_error = f"{type(e).__name__}: {e}"
        last_error_time = datetime.utcnow().isoformat() + "Z"
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


@app.route('/logs')
def logs_page():
    """A live HTML view of recent chat activity, straight from the
    conversations table — no need to dig through Render's log tab.
    Protected by a secret key set in Render's Environment tab (LOGS_KEY)."""

    logs_key = os.environ.get("LOGS_KEY")
    provided_key = request.args.get("key", "")

    if logs_key and not hmac.compare_digest(provided_key, logs_key):
        return Response(
            "🔒 Not authorized. Add ?key=YOUR_KEY to the URL.",
            status=401,
            mimetype="text/plain"
        )

    rows = db.get_recent_activity(limit=50)

    if rows:
        row_html = "\n".join(
            f"""
            <div class="entry">
                <div class="meta">
                    <span class="user">{escape(row['user_name'])}</span>
                    <span class="time">{escape(str(row['created_at']))}</span>
                </div>
                <div class="msg user-msg"><span class="label">User:</span> {escape(row['user_message'])}</div>
                <div class="msg ai-msg"><span class="label">Johnny:</span> {escape(row['ai_response'])}</div>
            </div>
            """
            for row in rows
        )
    else:
        row_html = '<p class="empty">No conversations logged yet. Send Johnny a message to see it here.</p>'

    page = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="15">
        <title>Johnny Tec — Live Logs</title>
        {PAGE_STYLE}
        <style>
            .entry {{
                background: #15151f;
                border: 1px solid #26263a;
                border-radius: 12px;
                padding: 14px 16px;
                margin-bottom: 14px;
            }}
            .meta {{
                display: flex;
                justify-content: space-between;
                font-size: 0.75rem;
                color: #8a8aa3;
                margin-bottom: 8px;
            }}
            .msg {{
                font-size: 0.95rem;
                line-height: 1.4;
                margin-bottom: 6px;
                word-wrap: break-word;
            }}
            .label {{ font-weight: 600; margin-right: 4px; }}
            .user-msg .label {{ color: #6ea8fe; }}
            .ai-msg .label {{ color: #b388ff; }}
            .empty {{ color: #8a8aa3; }}
        </style>
    </head>
    <body>
        <h1>Johnny Tec — Live Logs</h1>
        <p class="subtitle">Most recent 50 conversations · auto-refreshes every 15s</p>
        {row_html}
    </body>
    </html>
    """
    return Response(page, mimetype="text/html")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
