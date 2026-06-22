from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import librosa
import pretty_midi
import tempfile
import os
import traceback
import time
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

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

CHORD_TEMPLATES = {}
for chord_name, midi_notes in CHORD_NOTES.items():
    template = np.zeros(12)
    for n in midi_notes:
        template[n % 12] = 1
    CHORD_TEMPLATES[chord_name] = template

@app.get("/")
def home():
    return {"status": "Music backend is running"}

@app.get("/test")
def test():
    return {"success": True, "message": "API is working"}

def get_bpm(y, sr):
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if hasattr(tempo, "__len__"):
        return float(tempo[0])
    return float(tempo)

def detect_best_chord(chroma_vector):
    best_chord = "C"
    best_score = -1

    for chord_name, template in CHORD_TEMPLATES.items():
        score = float(np.dot(chroma_vector, template))
        if score > best_score:
            best_score = score
            best_chord = chord_name

    return best_chord

def detect_chord_progression(y, sr, bpm, max_chords=16):
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    duration = librosa.get_duration(y=y, sr=sr)

    beat_duration = 60.0 / bpm
    bar_duration = beat_duration * 4

    total_bars = max(4, int(duration / bar_duration))
    total_bars = min(total_bars, max_chords)

    chords = []

    for bar_index in range(total_bars):
        start_time = bar_index * bar_duration
        end_time = min((bar_index + 1) * bar_duration, duration)

        start_frame = librosa.time_to_frames(start_time, sr=sr)
        end_frame = librosa.time_to_frames(end_time, sr=sr)

        if end_frame <= start_frame:
            continue

        section = chroma[:, start_frame:end_frame]
        if section.size == 0:
            continue

        chroma_mean = section.mean(axis=1)
        chord = detect_best_chord(chroma_mean)
        chords.append(chord)

    if not chords:
        chords = ["C", "Am", "F", "G"]

    cleaned = []
    for chord in chords:
        if not cleaned or cleaned[-1] != chord:
            cleaned.append(chord)

    return cleaned[:max_chords]

def add_note(instrument, pitch, start, end, velocity):
    instrument.notes.append(
        pretty_midi.Note(
            velocity=int(velocity),
            pitch=int(pitch),
            start=float(start),
            end=float(end),
        )
    )

def add_chord(instrument, notes, start, duration, velocity):
    for note in notes:
        add_note(instrument, note, start, start + duration, velocity)

def add_bar_pattern(piano, bass, chord_name, start_time, beat_duration):
    notes = CHORD_NOTES.get(chord_name, CHORD_NOTES["C"])

    root = notes[0]
    third = notes[1]
    fifth = notes[2]

    bass_root = root - 24
    bass_fifth = fifth - 24

    add_note(bass, bass_root, start_time, start_time + beat_duration * 1.8, 82)
    add_note(bass, bass_fifth, start_time + beat_duration * 2, start_time + beat_duration * 3.8, 72)

    hit = beat_duration * 0.65

    add_chord(piano, [root, third, fifth], start_time, hit, 72)
    add_chord(piano, [third, fifth, root + 12], start_time + beat_duration, hit, 62)
    add_chord(piano, [root, third, fifth], start_time + beat_duration * 2, hit, 78)
    add_chord(piano, [third, fifth, root + 12], start_time + beat_duration * 3, hit, 66)

    add_note(piano, fifth + 12, start_time + beat_duration * 3.5, start_time + beat_duration * 3.9, 55)

def create_midi_from_chords(chords, bpm):
    request_id = int(time.time())

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)

    piano = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"),
        name="Right hand - " + "-".join(chords),
    )

    bass = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"),
        name="Left hand - " + "-".join(chords),
    )

    beat_duration = 60.0 / bpm
    bar_duration = beat_duration * 4
    current_time = 0.0

    for chord in chords:
        add_bar_pattern(piano, bass, chord, current_time, beat_duration)
        current_time += bar_duration

    midi.instruments.append(bass)
    midi.instruments.append(piano)

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mid").name
    midi.write(output_path)

    return output_path, request_id

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

        bpm = get_bpm(y, sr)
        duration = librosa.get_duration(y=y, sr=sr)
        chords = detect_chord_progression(y, sr, bpm, max_chords=8)

        notes = []
        for chord in chords[:3]:
            for pitch in CHORD_NOTES.get(chord, []):
                note = NOTE_NAMES[pitch % 12]
                if note not in notes:
                    notes.append(note)

        key = chords[0].replace("m", "") if chords else "C"

        return {
            "success": True,
            "bpm": round(bpm),
            "key": key,
            "notes": notes[:4],
            "suggested_chords": chords,
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

@app.post("/generate-accompaniment-from-audio")
async def generate_accompaniment_from_audio(file: UploadFile = File(...)):
    temp_path = None

    try:
        print("=== GENERATE FROM AUDIO CALLED ===")
        print("filename:", file.filename)

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

        bpm = round(get_bpm(y, sr))
        chords = detect_chord_progression(y, sr, bpm, max_chords=12)

        print("detected bpm:", bpm)
        print("detected chords:", chords)

        output_path, request_id = create_midi_from_chords(chords, bpm)

        print("generated midi:", output_path)
        print("midi size:", os.path.getsize(output_path))

        return FileResponse(
            output_path,
            media_type="audio/midi",
            filename=f"accompaniment_from_audio_{request_id}.mid",
        )

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Accompaniment from audio failed",
                "details": str(e),
            },
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/generate-accompaniment")
async def generate_accompaniment_fallback():
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "Use /generate-accompaniment-from-audio instead",
            "message": "This version needs the audio file itself to create a better accompaniment.",
        },
    )
