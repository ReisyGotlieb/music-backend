import librosa
import numpy as np

CHORD_TEMPLATES = {
    "C":  [1,0,0,0,1,0,0,1,0,0,0,0],
    "Cm": [1,0,0,1,0,0,0,1,0,0,0,0],
    "D":  [0,0,1,0,0,0,1,0,0,1,0,0],
    "Dm": [0,0,1,0,0,1,0,0,0,1,0,0],
    "E":  [0,0,0,0,1,0,0,0,1,0,0,1],
    "Em": [0,0,0,1,0,0,0,1,0,0,0,1],
    "F":  [1,0,0,0,0,1,0,0,1,0,0,0],
    "Fm": [1,0,0,0,1,0,0,0,1,0,0,0],
    "G":  [0,0,1,0,0,0,0,1,0,0,1,0],
    "Gm": [0,0,1,0,0,1,0,0,0,0,1,0],
    "A":  [1,0,0,1,0,0,0,0,0,1,0,0],
    "Am": [1,0,0,0,0,1,0,0,0,1,0,0],
    "B":  [0,1,0,0,1,0,0,0,0,0,1,0],
    "Bm": [0,1,0,0,0,1,0,0,0,0,1,0],
}


def detect_chords(y, sr, bpm):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

    chord_list = []

    for i in range(chroma.shape[1]):
        frame = chroma[:, i]

        best_score = -1
        best_chord = "C"

        for chord_name, template in CHORD_TEMPLATES.items():
            score = np.dot(frame, template)

            if score > best_score:
                best_score = score
                best_chord = chord_name

        chord_list.append(best_chord)

    compressed = []

    for chord in chord_list:
        if not compressed or compressed[-1] != chord:
            compressed.append(chord)

    return compressed[:16]
