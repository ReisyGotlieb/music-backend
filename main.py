import os
import uuid
import traceback
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ייבוא פונקציות העזר והשירותים מהפרויקט שלך
from services.audio_analysis import load_audio, detect_bpm, detect_duration
from services.chord_detection import detect_chords
from services.arranger import create_arrangement_plan
from services.midi_generator import generate_rich_midi
from services.audio_renderer import render_audio_from_midi, mix_vocal_and_accompaniment

app = FastAPI(
    title="Professional Music Generation Backend",
    description="Backend AI for automatically creating high-quality accompaniments and mixing them with vocal recordings.",
    version="1.0.0"
)

# הגדרת CORS כדי לאפשר ל-Bubble ולפרונטנד לתקשר עם ה-Backend בצורה מאובטחת
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # מומלץ להחליף לכתובת הדומיין הספציפית של ה-Bubble שלך בייצור
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def save_upload_to_temp(upload_file: UploadFile, content: bytes) -> str:
    """
    שומר את קובץ האודיו שהועלה מהפרונטנד לקובץ זמני בשרת לצורך עיבוד
    """
    suffix = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ".wav"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(content)
    temp_file.close()
    return temp_file.name

@app.get("/")
def read_root():
    """
    בדיקת תקינות בסיסית (Health Check) לשרת
    """
    return {"status": "online", "message": "Music Backend is running perfectly"}

@app.post("/generate-accompaniment-from-audio")
async def generate_accompaniment_from_audio(file: UploadFile = File(...)):
    """
    נתיב ה-API הראשי:
    1. מקבל קובץ שירה (Vocal) גולמי מהמשתמש.
    2. מנתח קצב, אורך ואקורדים.
    3. מייצר פלייבק מותאם אישית בפורמט MIDI.
    4. מרנדר את ה-MIDI לאודיו איכותי (WAV).
    5. מבצע מיקס ומאסטרינג בסיסי בין השירה לפלייבק.
    6. מחזיר קובץ MP3 סופי מוכן להשמעה.
    """
    temp_vocal_path = None
    midi_path = None
    backing_wav_path = None
    final_mp3_path = None
    
    try:
        # קריאת תוכן הקובץ שהועלה
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
            
        # 1. שמירת קובץ השירה הזמני
        temp_vocal_path = save_upload_to_temp(file, content)
        
        # 2. טעינת האודיו וניתוח מאפיינים בסיסיים
        y, sr = load_audio(temp_vocal_path)
        bpm = detect_bpm(y, sr)
        duration = detect_duration(y, sr)
        
        # הגבלת הגנה לקבצים ארוכים מדי (מומלץ כדי למנוע קריסת שרת בזמן עיבוד)
        if duration > 300:  # 5 דקות מקסימום
            raise HTTPException(status_code=400, detail="Audio duration exceeds the 5-minute limit")
            
        # 3. זיהוי אקורדים מתוך השירה של המשתמש
        chords = detect_chords(y, sr, bpm)
        
        # 4. בניית תוכנית עיבוד מוזיקלי (מבנה השיר, דינמיקה וכלים)
        arrangement = create_arrangement_plan(chords=chords, duration_seconds=duration)
        
        # 5. יצירת קובץ ה-MIDI המועשר (תווים, קווי בס, תפקידי פסנתר ותופים)
        midi_path, request_id, _ = generate_rich_midi(arrangement, bpm, target_duration=duration)
        
        # 6. רינדור ה-MIDI לצלילים אמיתיים באמצעות ה-SoundFont וה-FluidSynth
        backing_wav_path = render_audio_from_midi(midi_path)
        
        # 7. ביצוע מיקס מקצועי - איזון דציבלים וחיבור השירה יחד עם הליווי
        final_mp3_path = mix_vocal_and_accompaniment(temp_vocal_path, backing_wav_path)
        
        # 8. החזרת קובץ ה-MP3 המוגמר ישירות לנגן האודיו ב-Bubble
        return FileResponse(
            final_mp3_path,
            media_type="audio/mpeg",
            filename=f"pro_mix_{request_id}.mp3"
        )
        
    except HTTPException as http_ex:
        return JSONResponse(
            status_code=http_ex.status_code,
            content={"success": False, "error": http_ex.detail}
        )
    except Exception as e:
        # הדפסת שגיאה מלאה ללוגים של השרת לצורך בדיקות (Debugging)
        print("--- SERVER ERROR TRACEBACK ---")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False, 
                "error": "Internal processing error during song generation", 
                "details": str(e)
            }
        )
    finally:
        # ניקוי קבצים זמניים בסיום הפעולה כדי לשמור על שרת נקי
        for path in [temp_vocal_path, midi_path, backing_wav_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as clean_err:
                    print(f"Failed to remove temporary file {path}: {clean_err}")

if __name__ == "__main__":
    import uvicorn
    # הרצה מקומית על פורט 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
