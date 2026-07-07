import os
import subprocess
import tempfile
from midi2audio import FluidSynth

# הערה: עליך להוריד קובץ SoundFont איכותי (למשל GeneralUser GS או קובץ אחר בפורמט .sf2)
# ולשמור אותו בתיקיית הפרויקט שלך, למשל תחת תיקיית 'assets/default.sf2'
SOUNDFONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "default.sf2")

def render_audio_from_midi(midi_path: str) -> str:
    """
    מקבל נתיב לקובץ MIDI וממיר אותו לקובץ WAV איכותי באמצעות FluidSynth
    """
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found at {midi_path}")
        
    # יצירת קובץ זמני עבור ה-WAV המוכן
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav_path = temp_wav.name
    temp_wav.close()
    
    try:
        # בדיקה אם קובץ הסאונד-פונט קיים, אם לא - נשתמש בברירת המחדל של המערכת
        if os.path.exists(SOUNDFONT_PATH):
            fs = FluidSynth(sound_font=SOUNDFONT_PATH)
        else:
            print(f"Warning: Soundfont not found at {SOUNDFONT_PATH}, using system default.")
            fs = FluidSynth()
            
        # המרה של ה-MIDI ל-WAV
        fs.midi_to_audio(midi_path, temp_wav_path)
        return temp_wav_path
        
    except Exception as e:
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        raise RuntimeError(f"Failed to render MIDI to audio: {str(e)}")
