import librosa
import numpy as np

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]

MAJOR_PROGRESSIONS = {
    "C": ["C", "G", "Am", "F"],
    "D": ["D", "A", "Bm", "G"],
    "E": ["E", "B", "C#m", "A"],
    "F": ["F", "C", "Dm", "Bb"],
    "G": ["G", "D", "Em", "C"],
    "A": ["A", "E", "F#m", "D"],
    "B": ["B", "F#", "G#m", "E"],
}

MINOR_PROGRESSIONS = {
    "A": ["Am", "F", "C", "G"],
    "B": ["Bm", "G", "D", "A"],
    "C": ["Cm", "G#", "D#", "A#"],
    "D": ["Dm", "Bb", "F", "C"],
    "E": ["Em", "C", "G", "D"],
    "F": ["Fm", "C#", "G#", "D#"],
    "G": ["Gm", "D#", "A#", "F"],
}

def hz_to_note_name(freq):
    if freq <= 0:
        return None

    midi = int(round(librosa.hz_to_midi(freq)))
    return NOTE_NAMES[midi % 12]

def detect_vocal_melody_notes(y, sr):
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6")
    )

    notes = []

    if f0 is None:
        return notes

    for freq, voiced in zip(f0, voiced_flag):
        if voiced and freq is not None and not np.isnan(freq):
            note = hz_to_note_name(freq)
            if note:
                notes.append(note)

    return notes

def estimate_key_from_melody(notes):
    if not notes:
        return "C", "major"

    counts = {note: notes.count(note) for note in NOTE_NAMES}

    best_key = "C"
    best_mode = "major"
    best_score = -1

    for root_index, root_note in enumerate(NOTE_NAMES):
        major_notes = [NOTE_NAMES[(root_index + i) % 12] for i in MAJOR_SCALE]
        minor_notes = [NOTE_NAMES[(root_index + i) % 12] for i in MINOR_SCALE]

        major_score = sum(counts.get(n, 0) for n in major_notes)
        minor_score = sum(counts.get(n, 0) for n in minor_notes)

        if major_score > best_score:
            best_score = major_score
            best_key = root_note
            best_mode = "major"

        if minor_score > best_score:
            best_score = minor_score
            best_key = root_note
            best_mode = "minor"

    return best_key, best_mode

def generate_chords_from_vocal_melody(y, sr):
    notes = detect_vocal_melody_notes(y, sr)
    key, mode = estimate_key_from_melody(notes)

    base_key = key.replace("#", "")

    if mode == "minor":
        progression = MINOR_PROGRESSIONS.get(base_key, ["Am", "F", "C", "G"])
    else:
        progression = MAJOR_PROGRESSIONS.get(base_key, ["C", "G", "Am", "F"])

    duration = librosa.get_duration(y=y, sr=sr)

    repeats = max(2, int(duration // 8) + 1)

    chords = []
    for _ in range(repeats):
        chords.extend(progression)

    return {
        "notes": list(dict.fromkeys(notes[:40])),
        "key": key,
        "mode": mode,
        "chords": chords[:16]
    }
