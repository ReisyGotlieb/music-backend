import librosa
import numpy as np

CHORD_NOTES_PC = {
    "C": [0, 4, 7], "Cm": [0, 3, 7],
    "C#": [1, 5, 8], "C#m": [1, 4, 8],
    "D": [2, 6, 9], "Dm": [2, 5, 9],
    "D#": [3, 7, 10], "D#m": [3, 6, 10],
    "E": [4, 8, 11], "Em": [4, 7, 11],
    "F": [5, 9, 0], "Fm": [5, 8, 0],
    "F#": [6, 10, 1], "F#m": [6, 9, 1],
    "G": [7, 11, 2], "Gm": [7, 10, 2],
    "G#": [8, 0, 3], "G#m": [8, 11, 3],
    "A": [9, 1, 4], "Am": [9, 0, 4],
    "A#": [10, 2, 5], "A#m": [10, 1, 5],
    "B": [11, 3, 6], "Bm": [11, 2, 6],
}

def build_template(pcs):
    template = np.zeros(12)
    for pc in pcs:
        template[pc] = 1.0
    return template / (np.linalg.norm(template) + 1e-6)

CHORD_TEMPLATES = {
    name: build_template(pcs)
    for name, pcs in CHORD_NOTES_PC.items()
}

def best_chord(chroma_vector):
    chroma_vector = chroma_vector / (np.linalg.norm(chroma_vector) + 1e-6)

    best_name = "C"
    best_score = -1

    for name, template in CHORD_TEMPLATES.items():
        score = float(np.dot(chroma_vector, template))
        if score > best_score:
            best_score = score
            best_name = name

    return best_name

def smooth_chords(chords):
    if len(chords) < 3:
        return chords

    smoothed = chords[:]

    for i in range(1, len(chords) - 1):
        if chords[i - 1] == chords[i + 1] and chords[i] != chords[i - 1]:
            smoothed[i] = chords[i - 1]

    return smoothed

def detect_chords(y, sr, bpm):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    duration = librosa.get_duration(y=y, sr=sr)

    segment_seconds = 1.0
    chords = []

    t = 0.0

    while t < duration:
        start_frame = librosa.time_to_frames(t, sr=sr)
        end_frame = librosa.time_to_frames(min(t + segment_seconds, duration), sr=sr)

        if end_frame > start_frame:
            section = chroma[:, start_frame:end_frame]
            if section.size > 0:
                avg = section.mean(axis=1)
                chord = best_chord(avg)
                chords.append(chord)

        t += segment_seconds

    chords = smooth_chords(chords)

    return chords[:30] or ["C", "Am", "F", "G"]
