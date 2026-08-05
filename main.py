import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import db_connector

app = FastAPI(title="Johnny Tec AI Backend API", version="1.0")

# Enable CORS so your GitHub Pages dashboard can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client using environment variable
api_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

class ChatRequest(BaseModel):
    user_id: int = 1
    prompt: str

@app.get("/")
@app.get("/health")
def health_check():
    """Health status endpoint pinged by your GitHub Pages dashboard."""
    return {
        "status": "online",
        "service": "Johnny Tec AI Backend",
        "database_connected": os.path.exists(db_connector.DB_PATH),
        "ai_engine_ready": client is not None
    }

@app.post("/chat")
def generate_ai_response(request: ChatRequest):
    """Processes user queries, reads DB memories, generates AI output, and records history."""
    if not client:
        raise HTTPException(
            status_code=500, 
            detail="GEMINI_API_KEY environment variable is missing on server."
        )

    # 1. Fetch user memories from SQLite
    memories = db_connector.get_user_memories(request.user_id)
    memory_context = "\n".join(memories) if memories else "No prior memories recorded."

    # 2. Build contextual prompt
    full_prompt = f"User Memory Context:\n{memory_context}\n\nUser Message: {request.prompt}"

    try:
        # 3. Call Gemini AI Engine
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )
        ai_reply = response.text

        # 4. Save interaction back into SQLite database
        db_connector.save_conversation(request.user_id, request.prompt, ai_reply)

        return {
            "status": "success",
            "user_id": request.user_id,
            "prompt": request.prompt,
            "response": ai_reply
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
