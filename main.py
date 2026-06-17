from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import librosa
import tempfile
import os
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sing-to-song.lovable.app",
        "https://singto-song.lovable.app",
        "https://lovable.dev",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def home():
    return {"status": "Music backend is running"}

@app.post("/analyze-audio")
async def analyze_audio(file: UploadFile = File(...)):
    temp_path = None

    try:
        suffix = os.path.splitext(file.filename or "")[1].lower()

        if suffix not in [".mp3", ".wav"]:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Unsupported file type",
                    "message": "Please upload MP3 or WAV only",
                    "filename": file.filename
                }
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        y, sr = librosa.load(temp_path, sr=22050, mono=True, duration=30)

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

        return {
            "bpm": round(float(tempo)),
            "filename": file.filename,
            "sample_rate": sr,
            "duration_seconds": round(float(librosa.get_duration(y=y, sr=sr)), 2),
            "message": "Audio analyzed successfully"
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Audio analysis failed",
                "details": str(e),
                "trace": traceback.format_exc()
            }
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
