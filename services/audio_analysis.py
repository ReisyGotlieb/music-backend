import librosa

def load_audio(file_path):
    y, sr = librosa.load(
        file_path,
        sr=22050,
        mono=True,
        duration=30
    )

    return y, sr


def detect_bpm(y, sr):
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    if hasattr(tempo, "__len__"):
        return float(tempo[0])

    return float(tempo)


def detect_duration(y, sr):
    return librosa.get_duration(y=y, sr=sr)
