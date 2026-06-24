import pretty_midi
import tempfile
import os
import time

CHORD_NOTES = {
    "C": [60, 64, 67], "Cm": [60, 63, 67],
    "D": [62, 66, 69], "Dm": [62, 65, 69],
    "E": [64, 68, 71], "Em": [64, 67, 71],
    "F": [65, 69, 72], "Fm": [65, 68, 72],
    "G": [67, 71, 74], "Gm": [67, 70, 74],
    "A": [69, 73, 76], "Am": [69, 72, 76],
    "B": [71, 75, 78], "Bm": [71, 74, 78],
}

def add_note(instrument, pitch, start, end, velocity):
    instrument.notes.append(
        pretty_midi.Note(
            velocity=int(velocity),
            pitch=int(pitch),
            start=float(start),
            end=float(end),
        )
    )

def add_chord(instrument, notes, start, duration, velocity):
    for note in notes:
        add_note(instrument, note, start, start + duration, velocity)

def generate_rich_midi(chords, bpm):
    request_id = int(time.time())
    bpm = int(bpm or 90)

    clean_chords = [c for c in chords if c in CHORD_NOTES]
    if not clean_chords:
        clean_chords = ["C", "Am", "F", "G"]

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)

    piano = pretty_midi.Instrument(program=0, name="Piano")
    bass = pretty_midi.Instrument(program=32, name="Bass")
    strings = pretty_midi.Instrument(program=48, name="Strings Pad")
    arp = pretty_midi.Instrument(program=4, name="Arpeggio")
    drums = pretty_midi.Instrument(program=0, is_drum=True, name="Drums")

    beat = 60.0 / bpm
    current = 0.0

    for chord_index, chord in enumerate(clean_chords):
        notes = CHORD_NOTES[chord]
        root, third, fifth = notes

        # bass
        add_note(bass, root - 24, current, current + beat * 1.8, 85)
        add_note(bass, fifth - 24, current + beat * 2, current + beat * 3.8, 75)

        # piano rhythm
        add_chord(piano, [root, third, fifth], current, beat * 0.65, 76)
        add_chord(piano, [third, fifth, root + 12], current + beat, beat * 0.55, 62)
        add_chord(piano, [root, third, fifth], current + beat * 2, beat * 0.65, 80)
        add_chord(piano, [third, fifth, root + 12], current + beat * 3, beat * 0.55, 66)

        # strings long pad
        add_chord(strings, [root - 12, third, fifth], current, beat * 4, 45)

        # arpeggio
        arp_pattern = [root, third, fifth, root + 12, fifth, third, root, third]
        step = beat / 2
        for i, pitch in enumerate(arp_pattern):
            start = current + i * step
            add_note(arp, pitch + 12, start, start + step * 0.8, 58)

        # simple drums
        kick = 36
        snare = 38
        hihat = 42

        add_note(drums, kick, current, current + 0.05, 90)
        add_note(drums, snare, current + beat * 2, current + beat * 2 + 0.05, 78)

        for i in range(8):
            t = current + i * (beat / 2)
            add_note(drums, hihat, t, t + 0.03, 45)

        current += beat * 4

    midi.instruments.extend([bass, piano, strings, arp, drums])

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mid").name
    midi.write(output_path)

    return output_path, request_id, os.path.getsize(output_path)
