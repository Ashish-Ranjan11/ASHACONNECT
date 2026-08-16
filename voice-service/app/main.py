from pathlib import Path
import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.stt import transcribe_audio
from app.agent.router import router as voice_agent_router


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
    audio_path = Path(path)

    if not audio_path.exists():
        return {"success": False, "error": "Audio file not found"}

    return FileResponse(
        str(audio_path),
        media_type="audio/mpeg",
        filename="asha_response.mp3"
    )


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

app.include_router(voice_agent_router)
