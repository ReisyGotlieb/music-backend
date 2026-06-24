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

def add_drums(drums, start, seconds, bpm, intensity):
    beat = 60.0 / bpm
    kick = 36
    snare = 38
    closed_hat = 42
    open_hat = 46
    crash = 49

    t = start
    end = start + seconds
    beat_index = 0

    add_note(drums, crash, start, start + 0.08, 70 + intensity)

    while t < end:
        add_note(drums, closed_hat, t, t + 0.03, 38 + intensity)

        if beat_index % 4 == 0:
            add_note(drums, kick, t, t + 0.05, 75 + intensity)

        if beat_index % 4 == 2:
            add_note(drums, snare, t, t + 0.05, 70 + intensity)

        if beat_index % 8 == 7:
            add_note(drums, open_hat, t, t + 0.04, 45 + intensity)

        t += beat / 2
        beat_index += 1

def add_second_arrangement(piano, bass, pad, arp, chord, start, bpm, index):
    notes = CHORD_NOTES.get(chord, CHORD_NOTES["C"])
    root, third, fifth = notes

    beat = 60.0 / bpm
    end = start + 1.0

    intensity = min(20, index * 2)

    # Bass changes every second
    bass_note = root - 24 if index % 2 == 0 else fifth - 24
    add_note(bass, bass_note, start, end, 72 + intensity)

    # Pad holds harmony softly
    add_chord(pad, [root - 12, third, fifth], start, end, 38 + intensity)

    # Piano rhythmic hits
    hit_len = min(beat * 0.55, 0.35)

    add_chord(piano, [root, third, fifth], start, start + hit_len, 62 + intensity)

    if start + beat < end:
        add_chord(piano, [third, fifth, root + 12], start + beat, min(start + beat + hit_len, end), 55 + intensity)

    # Arpeggio inside each second
    arp_notes = [root, third, fifth, root + 12, fifth, third]
    step = 1.0 / len(arp_notes)

    for i, pitch in enumerate(arp_notes):
        s = start + i * step
        e = min(s + step * 0.75, end)
        add_note(arp, pitch + 12, s, e, 48 + random.randint(0, 10))

def generate_rich_midi(chords, bpm):
    request_id = int(time.time())
    bpm = int(bpm or 90)

    clean_chords = [c for c in chords if c in CHORD_NOTES]
    if not clean_chords:
        clean_chords = ["C", "Am", "F", "G"]

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)

    piano = pretty_midi.Instrument(program=0, name="Piano rhythmic")
    bass = pretty_midi.Instrument(program=33, name="Electric bass")
    pad = pretty_midi.Instrument(program=48, name="Strings pad")
    arp = pretty_midi.Instrument(program=4, name="Arpeggio")
    drums = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")

    total_seconds = len(clean_chords)

    for i, chord in enumerate(clean_chords):
        start = float(i)

        add_second_arrangement(
            piano=piano,
            bass=bass,
            pad=pad,
            arp=arp,
            chord=chord,
            start=start,
            bpm=bpm,
            index=i,
        )

    add_drums(
        drums=drums,
        start=0.0,
        seconds=float(total_seconds),
        bpm=bpm,
        intensity=12,
    )

    midi.instruments.extend([bass, pad, piano, arp, drums])

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mid").name
    midi.write(output_path)

    return output_path, request_id, os.path.getsize(output_path)
