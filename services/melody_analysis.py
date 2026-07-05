import librosa
import numpy as np
from collections import Counter

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

CHORDS_BY_KEY = {
    "C": ["C", "Dm", "Em", "F", "G", "Am"],
    "D": ["D", "Em", "F#m", "G", "A", "Bm"],
    "E": ["E", "F#m", "G#m", "A", "B", "C#m"],
    "F": ["F", "Gm", "Am", "Bb", "C", "Dm"],
    "G": ["G", "Am", "Bm", "C", "D", "Em"],
    "A": ["A", "Bm", "C#m", "D", "E", "F#m"],
    "B": ["B", "C#m", "D#m", "E", "F#", "G#m"],
}

CHORD_NOTES = {
    "C": ["C", "E", "G"], "Dm": ["D", "F", "A"], "Em": ["E", "G", "B"],
    "F": ["F", "A", "C"], "G": ["G", "B", "D"], "Am": ["A", "C", "E"],
    "D": ["D", "F#", "A"], "F#m": ["F#", "A", "C#"], "A": ["A", "C#", "E"],
    "Bm": ["B", "D", "F#"], "E": ["E", "G#", "B"], "G#m": ["G#", "B", "D#"],
    "B": ["B", "D#", "F#"], "C#m": ["C#", "E", "G#"], "D#m": ["D#", "F#", "A#"],
    "Gm": ["G", "A#", "D"], "Bb": ["A#", "D", "F"],
}

def hz_to_note(freq):
    if freq is None or np.isnan(freq) or freq <= 0:
        return None
    midi = int(round(librosa.hz_to_midi(freq)))
    return NOTE_NAMES[midi % 12]

def extract_timed_notes(y, sr):
    f0, voiced_flag, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6")
    )

    timed_notes = []
    if f0 is None:
        return timed_notes

    times = librosa.times_like(f0, sr=sr)

    last_note = None
    start_time = None

    for freq, voiced, t in zip(f0, voiced_flag, times):
        note = hz_to_note(freq) if voiced else None

        if note != last_note:
            if last_note is not None and start_time is not None:
                timed_notes.append({
                    "note": last_note,
                    "start": float(start_time),
                    "end": float(t)
                })

            last_note = note
            start_time = t if note is not None else None

    if last_note is not None and start_time is not None:
        timed_notes.append({
            "note": last_note,
            "start": float(start_time),
            "end": float(times[-1])
        })

    return [
        n for n in timed_notes
        if n["end"] - n["start"] >= 0.15
    ]

def estimate_key(timed_notes):
    notes = [n["note"] for n in timed_notes]
    if not notes:
        return "C"

    counter = Counter(notes)
    best_key = "C"
    best_score = -1

    for key, chords in CHORDS_BY_KEY.items():
        key_notes = set()
        for chord in chords:
            key_notes.update(CHORD_NOTES.get(chord, []))

        score = sum(counter.get(note, 0) for note in key_notes)

        if score > best_score:
            best_score = score
            best_key = key

    return best_key

def choose_chord_for_notes(notes, key):
    candidates = CHORDS_BY_KEY.get(key, CHORDS_BY_KEY["C"])

    best_chord = candidates[0]
    best_score = -1

    for chord in candidates:
        chord_notes = set(CHORD_NOTES.get(chord, []))
        score = 0

        for note in notes:
            if note in chord_notes:
                score += 3
            elif note == chord.replace("m", ""):
                score += 2
            else:
                score -= 1

        if score > best_score:
            best_score = score
            best_chord = chord

    return best_chord

def build_vocal_harmony(y, sr):
    timed_notes = extract_timed_notes(y, sr)
    key = estimate_key(timed_notes)

    duration = librosa.get_duration(y=y, sr=sr)
    segment_seconds = 2.0

    arrangement_chords = []
    t = 0.0

    while t < duration:
        segment_notes = [
            n["note"] for n in timed_notes
            if n["start"] < t + segment_seconds and n["end"] > t
        ]

        if segment_notes:
            chord = choose_chord_for_notes(segment_notes, key)
        else:
            chord = arrangement_chords[-1]["chord"] if arrangement_chords else key

        if not arrangement_chords or arrangement_chords[-1]["chord"] != chord:
            arrangement_chords.append({
                "chord": chord,
                "start": float(t),
                "end": float(min(t + segment_seconds, duration))
            })
        else:
            arrangement_chords[-1]["end"] = float(min(t + segment_seconds, duration))

        t += segment_seconds

    notes_unique = list(dict.fromkeys([n["note"] for n in timed_notes]))

    return {
        "key": key,
        "mode": "major",
        "notes": notes_unique[:20],
        "chords": [c["chord"] for c in arrangement_chords],
        "timeline": arrangement_chords
    }

def generate_chords_from_vocal_melody(y, sr):
    return build_vocal_harmony(y, sr)
