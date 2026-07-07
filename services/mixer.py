from pydub import AudioSegment

def mix_vocal_and_accompaniment(vocal_path: str, accompaniment_path: str) -> str:
    """
    מערבב את קול הזמר עם הפלייבק שנוצר ומפיק קובץ MP3 סופי מוכן להאזנה
    """
    # טעינת שני הקבצים
    vocal = AudioSegment.from_file(vocal_path)
    backing = AudioSegment.from_file(accompaniment_path)
    
    # שלב הפקה מקצועי: ננמיך מעט את הפלייבק כדי שהזמר "יישב מעליו" ולא ייבלע
    # ננמיך את הפלייבק ב-3 דציבלים, ונגביר את הזמר ב-1 דציבל (לדוגמה)
    backing = backing - 3
    vocal = vocal + 1
    
    # התאמת אורך (אם אחד הקבצים ארוך מהשני, נחתוך לפי האורך של הפלייבק או השירה)
    # בדרך כלל נרצה לשלב אותם מהתחלה (position 0)
    mixed_audio = backing.overlay(vocal, position=0)
    
    # שמירת הקובץ הסופי כ-MP3 באיכות גבוהה (320kbps) כדי שזה יישמע מקצועי
    output_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    output_path = output_temp.name
    output_temp.close()
    
    mixed_audio.export(output_path, format="mp3", bitrate="320k")
    return output_path
