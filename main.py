from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import tempfile
import os
import traceback

from services.audio_analysis import load_audio, detect_bpm, detect_duration
from services.chord_detection import detect_chords
from services.arranger import create_arrangement_plan
from services.midi_generator import generate_rich_midi

app = FastAPI()

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
    return {"success": True, "message": "API is working"}

def save_upload_to_temp(file: UploadFile, content: bytes):
    suffix = os.path.splitext(file.filename or "")[1].lower()

   if suffix not in [".mp3", ".wav", ".webm", ".ogg", ".m4a"]:
        raise "Please upload MP3, WAV, WEBM, OGG or M4A"
       
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(content)
    temp_file.close()

    return temp_file.name

@app.post("/analyze-audio")
async def analyze_audio(file: UploadFile = File(...)):
    temp_path = None

    try:
        content = await file.read()
        temp_path = save_upload_to_temp(file, content)

        y, sr = load_audio(temp_path)

        bpm = round(detect_bpm(y, sr))
        duration = detect_duration(y, sr)
        chords = detect_chords(y, sr, bpm)

        return {
            "success": True,
            "bpm": bpm,
            "key": chords[0].replace("m", "") if chords else "C",
            "notes": [],
            "suggested_chords": chords,
            "filename": file.filename,
            "sample_rate": sr,
            "duration_seconds": round(float(duration), 2),
            "message": "Audio analyzed successfully",
        }

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Unsupported file type", "details": str(e)},
        )

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Audio analysis failed", "details": str(e)},
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/generate-accompaniment-from-audio")
async def generate_accompaniment_from_audio(file: UploadFile = File(...)):
    temp_path = None

    try:
        print("=" * 60)
        print("GENERATE ACCOMPANIMENT - STABLE MODE")
        print("FILE:", file.filename)
        print("=" * 60)

        content = await file.read()
        temp_path = save_upload_to_temp(file, content)

        y, sr = load_audio(temp_path)

        bpm = round(detect_bpm(y, sr))
        duration = detect_duration(y, sr)
        chords = detect_chords(y, sr, bpm)

        print("Detected BPM:", bpm)
        print("Detected duration:", duration)
        print("Detected chords:", chords)

        arrangement = create_arrangement_plan(
            chords=chords,
            duration_seconds=duration,
        )

        output_path, request_id, file_size = generate_rich_midi(
            arrangement,
            bpm,
            target_duration=duration,
        )

        print("Generated MIDI:", output_path)
        print("MIDI size:", file_size)

        return FileResponse(
            output_path,
            media_type="audio/midi",
            filename=f"stable_accompaniment_{request_id}.mid",
        )

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Unsupported file type", "details": str(e)},
        )

    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Stable accompaniment generation failed",
                "details": str(e),
            },
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/generate-accompaniment")
async def generate_accompaniment_old():
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "Use /generate-accompaniment-from-audio instead",
        },
    )
