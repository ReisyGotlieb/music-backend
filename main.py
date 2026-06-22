from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import librosa
import pretty_midi
import tempfile
import os
import traceback
import time

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
                    "filename": file.filename,
                },
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
            "message": "Audio analyzed successfully",
        }

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Audio analysis failed",
                "details": str(e),
            },
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

def add_note(instrument, pitch, start, end, velocity):
    instrument.notes.append(
        pretty_midi.Note(
            velocity=velocity,
            pitch=int(pitch),
            start=float(start),
            end=float(end),
        )
    )

def add_chord_hit(instrument, notes, start, duration, velocity):
    for pitch in notes:
        add_note(instrument, pitch, start, start + duration, velocity)

def add_accompaniment_pattern(piano, bass, chord_name, start_time, beat_duration):
    notes = CHORD_NOTES.get(chord_name, CHORD_NOTES["C"])

    root = notes[0]
    third = notes[1]
    fifth = notes[2]

    bass_root = root - 24
    bass_fifth = fifth - 24

    # תיבה אחת = 4 פעימות
    # יד שמאל: בס פעימה 1 + חמישית פעימה 3
    add_note(bass, bass_root, start_time, start_time + beat_duration * 1.8, 82)
    add_note(bass, bass_fifth, start_time + beat_duration * 2, start_time + beat_duration * 3.8, 70)

    # יד ימין: תבנית קצבית יותר חיה
    hit_duration = beat_duration * 0.75

    add_chord_hit(piano, [root, third, fifth], start_time, hit_duration, 72)
    add_chord_hit(piano, [third, fifth, root + 12], start_time + beat_duration, hit_duration, 64)
    add_chord_hit(piano, [root, third, fifth], start_time + beat_duration * 2, hit_duration, 76)
    add_chord_hit(piano, [third, fifth, root + 12], start_time + beat_duration * 3, hit_duration, 66)

    # צליל מעבר קטן בסוף התיבה
    add_note(piano, fifth + 12, start_time + beat_duration * 3.5, start_time + beat_duration * 3.9, 54)

@app.post("/generate-accompaniment")
async def generate_accompaniment(data: AccompanimentRequest):
    output_path = None

    try:
        request_id = int(time.time())
        bpm = int(data.bpm or 90)
        chords = data.chords or ["C", "Am", "F", "G"]

        clean_chords = []
        for chord in chords:
            if chord in CHORD_NOTES:
                clean_chords.append(chord)

        if not clean_chords:
            clean_chords = ["C", "Am", "F", "G"]

        print("generate-accompaniment called")
        print("request_id:", request_id)
        print("received bpm:", bpm)
        print("received chords:", clean_chords)

        midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)

        piano = pretty_midi.Instrument(
            program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"),
            name="Right hand chords - " + "-".join(clean_chords),
        )

        bass = pretty_midi.Instrument(
            program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"),
            name="Left hand bass - " + "-".join(clean_chords),
        )

        beat_duration = 60.0 / bpm
        bar_duration = beat_duration * 4

        current_time = 0.0

        # 4 סבבים של האקורדים, כדי שיהיה קובץ יותר ארוך וברור
        repeats = 4

        for repeat_index in range(repeats):
            for chord_name in clean_chords:
                add_accompaniment_pattern(
                    piano=piano,
                    bass=bass,
                    chord_name=chord_name,
                    start_time=current_time,
                    beat_duration=beat_duration,
                )
                current_time += bar_duration

        midi.instruments.append(bass)
        midi.instruments.append(piano)

        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mid").name
        midi.write(output_path)

        file_size = os.path.getsize(output_path)
        print("generated midi path:", output_path)
        print("generated midi size:", file_size)

        return FileResponse(
            output_path,
            media_type="audio/midi",
            filename=f"accompaniment_{request_id}.mid",
        )

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Accompaniment generation failed",
                "details": str(e),
            },
        )
