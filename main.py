from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import librosa
import pretty_midi
import tempfile
import os
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

CHORD_MAP = {
    "C": ["C", "Am", "F", "G"],
    "C#": ["C#", "A#m", "F#", "G#"],
    "D": ["D", "Bm", "G", "A"],
    "D#": ["D#", "Cm", "G#", "A#"],
    "E": ["E", "C#m", "A", "B"],
    "F": ["F", "Dm", "Bb", "C"],
    "F#": ["F#", "D#m", "B", "C#"],
    "G": ["G", "Em", "C", "D"],
    "G#": ["G#", "Fm", "C#", "D#"],
    "A": ["A", "F#m", "D", "E"],
    "A#": ["A#", "Gm", "D#", "F"],
    "B": ["B", "G#m", "E", "F#"],
}

CHORD_NOTES = {
    "C": [60, 64, 67], "Cm": [60, 63, 67],
    "C#": [61, 65, 68], "C#m": [61, 64, 68],
    "D": [62, 66, 69], "Dm": [62, 65, 69],
    "D#": [63, 67, 70], "D#m": [63, 66, 70],
    "E": [64, 68, 71], "Em": [64, 67, 71],
    "F": [65, 69, 72], "Fm": [65, 68, 72],
    "F#": [66, 70, 73], "F#m": [66, 69, 73],
    "G": [67, 71, 74], "Gm": [67, 70, 74],
    "G#": [68, 72, 75], "G#m": [68, 71, 75],
    "A": [69, 73, 76], "Am": [69, 72, 76],
    "A#": [70, 74, 77], "A#m": [70, 73, 77],
    "B": [71, 75, 78], "Bm": [71, 74, 78],
}

class AccompanimentRequest(BaseModel):
    bpm: int
    chords: list[str]

@app.get("/")
def home():
    return {"status": "Music backend is running"}

@app.get("/test")
def test():
    return {"success": True, "message": "API is working"}

def analyze_notes_and_key(y, sr):
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)

    top_notes_idx = chroma_mean.argsort()[-3:][::-1]
    top_notes = [NOTE_NAMES[int(i)] for i in top_notes_idx]

    detected_key = top_notes[0]
    suggested_chords = CHORD_MAP.get(detected_key, [detected_key])

    return detected_key, top_notes, suggested_chords

@app.post("/analyze-audio")
async def analyze_audio(file: UploadFile = File(...)):
    temp_path = None

    try:
        suffix = os.path.splitext(file.filename or "")[1].lower()

        if suffix not in [".mp3", ".wav"]:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
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

        if hasattr(tempo, "__len__"):
            tempo_value = float(tempo[0])
        else:
            tempo_value = float(tempo)

        duration = librosa.get_duration(y=y, sr=sr)
        detected_key, top_notes, suggested_chords = analyze_notes_and_key(y, sr)

        return {
            "success": True,
            "bpm": round(tempo_value),
            "key": detected_key,
            "notes": top_notes,
            "suggested_chords": suggested_chords,
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

@app.post("/generate-accompaniment")
async def generate_accompaniment(data: AccompanimentRequest):
    try:
        bpm = data.bpm or 90
        chords = data.chords or ["C", "Am", "F", "G"]

        midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
        piano = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"))

        beat_duration = 60 / bpm
        chord_duration = beat_duration * 4

        current_time = 0.0

        for chord in chords:
            notes = CHORD_NOTES.get(chord, CHORD_NOTES["C"])

            for note_number in notes:
                note = pretty_midi.Note(
                    velocity=80,
                    pitch=note_number,
                    start=current_time,
                    end=current_time + chord_duration
                )
                piano.notes.append(note)

            current_time += chord_duration

        midi.instruments.append(piano)

        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mid").name
        midi.write(output_path)

        return FileResponse(
            output_path,
            media_type="audio/midi",
            filename="accompaniment.mid"
        )

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Accompaniment generation failed",
                "details": str(e)
            }
        )
