import pretty_midi
import tempfile
import os
import time
import random

CHORD_NOTES = {
    "C": [60, 64, 67], "Cm": [60, 63, 67],
    "C#": [61, 65, 68], "C#m": [61, 64, 68],
    "D": [62, 66, 69], "Dm": [62, 65, 69],
    "D#": [63, 67, 70], "D#m": [63, 66, 70],
    "E": [64, 68, 71], "Em": [64, 67, 71],
    "F": [65, 69, 72], "Fm": [65, 68, 72],
    "F#": [66, 70, 73], "F#m": [66, 69, 73],
    "G": [67, 71, 74], "Gm": [67, 70, 74],
    "G#": [68, 72, 75], "G#m": [68, 71, 75],
    "A": [69, 73, 76], "Am": [69, 72, 76],
    "A#": [70, 74, 77], "A#m": [70, 73, 77],
    "B": [71, 75, 78], "Bm": [71, 74, 78],
}

def add_note(inst, pitch, start, end, velocity):
    inst.notes.append(
        pretty_midi.Note(
            velocity=int(velocity),
            pitch=int(pitch),
            start=float(start),
            end=float(end),
        )
    )

def add_chord(inst, notes, start, end, velocity):
    for n in notes:
        add_note(inst, n, start, end, velocity)

def get_velocity_base(intensity):
    if intensity == "soft":
        return 45
    if intensity == "medium":
        return 62
    return 78

def normalize_arrangement(input_items):
    arrangement = []

    for index, item in enumerate(input_items):
        if isinstance(item, dict):
            chord = item.get("chord", "C")
            intensity = item.get("intensity", "medium")
            use_drums = item.get("use_drums", True)
            use_arpeggio = item.get("use_arpeggio", True)
        else:
            chord = item
            intensity = "medium"
            use_drums = True
            use_arpeggio = True

        if chord not in CHORD_NOTES:
            chord = "C"

        arrangement.append({
            "chord": chord,
            "intensity": intensity,
            "use_drums": use_drums,
            "use_arpeggio": use_arpeggio,
            "bar_index": index,
        })

    return arrangement or [
        {"chord": "C", "intensity": "soft", "use_drums": False, "use_arpeggio": False, "bar_index": 0},
        {"chord": "G", "intensity": "medium", "use_drums": True, "use_arpeggio": False, "bar_index": 1},
        {"chord": "Am", "intensity": "full", "use_drums": True, "use_arpeggio": True, "bar_index": 2},
        {"chord": "F", "intensity": "full", "use_drums": True, "use_arpeggio": True, "bar_index": 3},
    ]

def add_drums(drums, start, bar_seconds, bpm, intensity):
    beat = 60.0 / bpm
    kick = 36
    snare = 38
    closed_hat = 42
    open_hat = 46
    crash = 49

    v = get_velocity_base(intensity)

    add_note(drums, crash, start, start + 0.08, min(100, v + 15))

    for i in range(8):
        t = start + i * (beat / 2)
        add_note(drums, closed_hat, t, t + 0.03, min(90, v - 10))

    add_note(drums, kick, start, start + 0.05, min(110, v + 18))
    add_note(drums, snare, start + beat * 2, start + beat * 2 + 0.05, min(105, v + 8))

    if intensity == "full":
        add_note(drums, kick, start + beat * 2.5, start + beat * 2.5 + 0.05, min(105, v + 10))
        add_note(drums, open_hat, start + beat * 3.5, start + beat * 3.5 + 0.05, min(95, v))

def add_bar_arrangement(piano, bass, pad, arp, item, start, bpm):
    chord = item["chord"]
    intensity = item["intensity"]
    use_arpeggio = item["use_arpeggio"]

    notes = CHORD_NOTES.get(chord, CHORD_NOTES["C"])
    root, third, fifth = notes

    beat = 60.0 / bpm
    bar_end = start + beat * 4
    v = get_velocity_base(intensity)

    add_note(bass, root - 24, start, start + beat * 1.8, min(110, v + 22))
    add_note(bass, fifth - 24, start + beat * 2, start + beat * 3.8, min(105, v + 12))

    add_chord(pad, [root - 12, third, fifth], start, bar_end, max(28, v - 18))

    hit = beat * 0.65
    add_chord(piano, [root, third, fifth], start, start + hit, min(105, v + 5))
    add_chord(piano, [third, fifth, root + 12], start + beat, start + beat + hit, max(40, v - 8))
    add_chord(piano, [root, third, fifth], start + beat * 2, start + beat * 2 + hit, min(110, v + 8))
    add_chord(piano, [third, fifth, root + 12], start + beat * 3, start + beat * 3 + hit, max(42, v - 5))

    if use_arpeggio:
        arp_notes = [root, third, fifth, root + 12, fifth, third, root, fifth]
        step = beat / 2

        for i, pitch in enumerate(arp_notes):
            s = start + i * step
            add_note(
                arp,
                pitch + 12,
                s,
                s + step * 0.75,
                max(35, min(90, v - 12 + random.randint(0, 10))),
            )

def generate_rich_midi(arrangement_items, bpm):
    request_id = int(time.time())
    bpm = int(bpm or 90)
    arrangement = normalize_arrangement(arrangement_items)

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)

    piano = pretty_midi.Instrument(program=0, name="Piano rhythmic")
    bass = pretty_midi.Instrument(program=33, name="Electric bass")
    pad = pretty_midi.Instrument(program=48, name="Strings pad")
    arp = pretty_midi.Instrument(program=4, name="Arpeggio")
    drums = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")

    beat = 60.0 / bpm
    bar_seconds = beat * 4

    for i, item in enumerate(arrangement):
        start = i * bar_seconds

        add_bar_arrangement(
            piano=piano,
            bass=bass,
            pad=pad,
            arp=arp,
            item=item,
            start=start,
            bpm=bpm,
        )

        if item["use_drums"]:
            add_drums(
                drums=drums,
                start=start,
                bar_seconds=bar_seconds,
                bpm=bpm,
                intensity=item["intensity"],
            )

    midi.instruments.extend([bass, pad, piano, arp, drums])

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mid").name
    midi.write(output_path)

    return output_path, request_id, os.path.getsize(output_path)
