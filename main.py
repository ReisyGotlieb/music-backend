from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import librosa
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Music backend is running"}

@app.post("/analyze-audio")
async def analyze_audio(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1] or ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name

    y, sr = librosa.load(temp_path)

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

    return {
        "bpm": round(float(tempo)),
        "filename": file.filename,
        "message": "Audio analyzed successfully"
    }
