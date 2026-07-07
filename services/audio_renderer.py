import os
import tempfile
import numpy as np
import soundfile as sf
import pretty_midi
from pydub import AudioSegment

def render_audio_from_midi(midi_path: str) -> str:
    """
    מרנדר קובץ MIDI לאודיו WAV בצורה נקייה ויציבה באמצעות פייתון בלבד (ללא FluidSynth)
    """
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found at {midi_path}")
        
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav_path = temp_wav.name
    temp_wav.close()
    
    try:
        # טעינת ה-MIDI באמצעות pretty_midi
        pm = pretty_midi.PrettyMIDI(midi_path)
        
        # סינתזה של ה-MIDI לסיגנל אודיו (קצב דגימה סטנדרטי 44100)
        # הפונקציה הזו מייצרת סאונד דיגיטלי ישירות מהתווים
        audio_data = pm.synthesize(fs=44100)
        
        # נרמול עוצמת השמע כדי למנוע עיוותים (Clipping)
        if len(audio_data) > 0:
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val
                
        # שמירת האודיו שנוצר לקובץ WAV זמני
        sf.write(temp_wav_path, audio_data, 44100)
        return temp_wav_path
        
    except Exception as e:
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        raise RuntimeError(f"Failed to synthesize MIDI to audio: {str(e)}")


def mix_vocal_and_accompaniment(vocal_path: str, accompaniment_path: str) -> str:
    """
    מערבב את השירה המקורית עם הליווי הדיגיטלי שנוצר
    """
    if not os.path.exists(vocal_path):
        raise FileNotFoundError(f"Vocal file not found at {vocal_path}")
    if not os.path.exists(accompaniment_path):
        raise FileNotFoundError(f"Accompaniment file not found at {accompaniment_path}")

    # טעינת הקבצים ב-pydub
    vocal = AudioSegment.from_file(vocal_path)
    backing = AudioSegment.from_file(accompaniment_path)
    
    # התאמת עוצמות עדינה
    backing = backing - 4  # הנמכת הליווי כדי שהשירה תבלוט
    vocal = vocal + 1      # חיזוק עדין לשירה
    
    # שילוב האודיו
    mixed_audio = backing.overlay(vocal, position=0)
    
    # שמירה כ-MP3 באיכות גבוהה
    output_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    output_path = output_temp.name
    output_temp.close()
    
    mixed_audio.export(output_path, format="mp3", bitrate="320k")
    return output_path
