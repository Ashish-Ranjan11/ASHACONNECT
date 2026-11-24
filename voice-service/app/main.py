from pathlib import Path
import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.stt import transcribe_audio
from app.agent.router import router as voice_agent_router
from app.agent.live_router import gemini_live_socket


app = FastAPI(
    title="ASHA Connect Voice Service",
    version="0.3.0",
    description="Multilingual voice interface for ASHA Connect"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/voice/audio")
def get_voice_audio(path: str):
    """
    Serve generated TTS audio to the frontend.
    """
    raise HTTPException(status_code=410, detail="Legacy audio download disabled; use authenticated Gemini Live streaming.")


@app.get("/")
def root():
    return {
        "service": "ASHA Connect Voice Service",
        "status": "running",
        "version": "0.3.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "stt": "IndicConformer",
        "languages": [
            "hi",
            "ne",
            "en"
        ]
    }


@app.post("/voice/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("hi")
):

    raise HTTPException(status_code=410, detail="Use authenticated Gemini Live streaming")
    suffix = os.path.splitext(
        audio.filename or ".wav"
    )[1]

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    ) as temp:

        content = await audio.read()
        temp.write(content)
        temp_path = temp.name

    try:

        text = transcribe_audio(
            temp_path,
            language=language
        )

        return {
            "success": True,
            "language": language,
            "text": text
        }

    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)

# Legacy agent endpoints disabled in production; use authenticated Live socket.


# Gemini Live native-audio WebSocket
app.add_api_websocket_route(
    "/voice/live",
    gemini_live_socket,
)
