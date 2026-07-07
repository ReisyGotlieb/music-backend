import os
import subprocess
import tempfile
from midi2audio import FluidSynth
from pydub import AudioSegment

# נתיבי ה-SoundFont (בודק קודם בתיקיית assets ואז בברירת המחדל של השרת)
SOUNDFONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "default.sf2")
SYSTEM_SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"

def render_audio_from_midi(midi_path: str) -> str:
    """
    מקבל נתיב לקובץ MIDI וממיר אותו לקובץ WAV באמצעות FluidSynth
    """
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found at {midi_path}")
        
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav_path = temp_wav.name
    temp_wav.close()
    
    try:
        # קביעת ה-SoundFont המתאים לפי מה שקיים בשרת
        if os.path.exists(SOUNDFONT_PATH):
            fs = FluidSynth(sound_font=SOUNDFONT_PATH)
        elif os.path.exists(SYSTEM_SOUNDFONT):
            fs = FluidSynth(sound_font=SYSTEM_SOUNDFONT)
        else:
            print("Warning: No specific soundfont found, using system default.")
            fs = FluidSynth()
            
        fs.midi_to_audio(midi_path, temp_wav_path)
        return temp_wav_path
        
    except Exception as e:
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        raise RuntimeError(f"Failed to render MIDI to audio: {str(e)}")


def mix_vocal_and_accompaniment(vocal_path: str, accompaniment_path: str) -> str:
    """
    מבצע מיקס: משלב את קול הזמר המקורי יחד עם קובץ הליווי (הפלייבק) שרונדר
    """
    if not os.path.exists(vocal_path):
        raise FileNotFoundError(f"Vocal file not found at {vocal_path}")
    if not os.path.exists(accompaniment_path):
        raise FileNotFoundError(f"Accompaniment file not found at {accompaniment_path}")

    # טעינת שני קבצי השמע
    vocal = AudioSegment.from_file(vocal_path)
    backing = AudioSegment.from_file(accompaniment_path)
    
    # איזון עוצמות בסיסי כדי שהשירה תישמע מעל הליווי
    backing = backing - 3  # הנמכת הפלייבק ב-3 דציבלים
    vocal = vocal + 1      # הגברת הווקאל ב-1 דציבל
    
    # שילוב האודיו (Overlay) החל מנקודת ההתחלה
    mixed_audio = backing.overlay(vocal, position=0)
    
    # שמירה כקובץ MP3 זמני באיכות גבוהה (320kbps)
    output_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    output_path = output_temp.name
    output_temp.close()
    
    mixed_audio.export(output_path, format="mp3", bitrate="320k")
    return output_path
