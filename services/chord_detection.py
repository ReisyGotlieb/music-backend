import librosa
import numpy as np

CHORD_TEMPLATES = {
    "C":  [1,0,0,0,1,0,0,1,0,0,0,0], "Cm": [1,0,0,1,0,0,0,1,0,0,0,0],
    "D":  [0,0,1,0,0,0,1,0,0,1,0,0], "Dm": [0,0,1,0,0,1,0,0,0,1,0,0],
    "E":  [0,0,0,0,1,0,0,0,1,0,0,1], "Em": [0,0,0,1,0,0,0,1,0,0,0,1],
    "F":  [1,0,0,0,0,1,0,0,1,0,0,0], "Fm": [1,0,0,0,1,0,0,0,1,0,0,0],
    "G":  [0,0,1,0,0,0,0,1,0,0,1,0], "Gm": [0,0,1,0,0,1,0,0,0,0,1,0],
    "A":  [1,0,0,1,0,0,0,0,0,1,0,0], "Am": [1,0,0,0,0,1,0,0,0,1,0,0],
    "B":  [0,1,0,0,1,0,0,0,0,0,1,0], "Bm": [0,1,0,0,0,1,0,0,0,0,1,0],
}

def best_chord(chroma_vector):
    chroma_vector = chroma_vector / (np.linalg.norm(chroma_vector) + 1e-6)

    best = "C"
    best_score = -1

    for name, template in CHORD_TEMPLATES.items():
        template = np.array(template, dtype=float)
        template = template / (np.linalg.norm(template) + 1e-6)
        score = float(np.dot(chroma_vector, template))

        if score > best_score:
            best_score = score
            best = name

    return best

def detect_chords(y, sr, bpm):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    duration = librosa.get_duration(y=y, sr=sr)

    beat = 60.0 / max(bpm, 1)
    segment = beat * 2  # חצי תיבה במקום פריים-פריים

    chords = []
    t = 0.0

    while t < duration:
        start_frame = librosa.time_to_frames(t, sr=sr)
        end_frame = librosa.time_to_frames(min(t + segment, duration), sr=sr)

        if end_frame > start_frame:
            section = chroma[:, start_frame:end_frame]
            if section.size > 0:
                avg = section.mean(axis=1)
                chords.append(best_chord(avg))

        t += segment

    compressed = []
    for chord in chords:
        if not compressed or compressed[-1] != chord:
            compressed.append(chord)

    return compressed[:12] or ["C", "Am", "F", "G"]
