from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import librosa
import tempfile
import os
import traceback

app = FastAPI()

# CORS - פתוח לגמרי לצורך בדיקות
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Music backend is running"}


@app.get("/test")
def test():
    return {
        "success": True,
        "message": "API is working"
    }


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

        # טעינה חסכונית בזיכרון
        y, sr = librosa.load(
            temp_path,
            sr=22050,
            mono=True,
            duration=30
        )

       tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

if hasattr(tempo, "__len__"):
    tempo_value = float(tempo[0])
else:
    tempo_value = float(tempo)

duration = librosa.get_duration(y=y, sr=sr)

return {
    "success": True,
    "bpm": round(tempo_value),
    "filename": file.filename,
    "sample_rate": sr,
    "duration_seconds": round(float(duration), 2),
    "message": "Audio analyzed successfully"
}

    except Exception as e:
        print(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Audio analysis failed",
                "details": str(e)
            }
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
