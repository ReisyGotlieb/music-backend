from collections import Counter

DIATONIC_PROGRESSIONS = {
    "C": ["C", "G", "Am", "F"],
    "D": ["D", "A", "Bm", "G"],
    "E": ["E", "B", "C#m", "A"],
    "F": ["F", "C", "Dm", "Bb"],
    "G": ["G", "D", "Em", "C"],
    "A": ["A", "E", "F#m", "D"],
    "B": ["B", "F#", "G#m", "E"],
}

NOTE_TO_KEY = {
    "C": "C", "D": "D", "E": "E", "F": "F",
    "G": "G", "A": "A", "B": "B",
    "C#": "D", "D#": "E", "F#": "G",
    "G#": "A", "A#": "B",
}

def choose_key_from_melody(notes):
    if not notes:
        return "C"

    counter = Counter(notes)
    most_common_note = counter.most_common(1)[0][0]

    return NOTE_TO_KEY.get(most_common_note, "C")

def build_harmony_from_melody(notes, duration_seconds):
    key = choose_key_from_melody(notes)

    base_progression = DIATONIC_PROGRESSIONS.get(
        key,
        ["C", "G", "Am", "F"]
    )

    if duration_seconds <= 10:
        repeats = 2
    elif duration_seconds <= 20:
        repeats = 4
    else:
        repeats = 6

    chords = []

    for _ in range(repeats):
        chords.extend(base_progression)

    return {
        "key": key,
        "chords": chords,
        "style": "rich_pop_accompaniment"
    }
