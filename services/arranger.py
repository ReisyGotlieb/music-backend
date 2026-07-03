def create_arrangement_plan(chords, duration_seconds):
    plan = []

    if not chords:
        chords = ["C", "G", "Am", "F"]

    section_length = max(1, len(chords) // 3)

    for index, chord in enumerate(chords):
        if index < section_length:
            intensity = "soft"
            drums = False
            arp = False
        elif index < section_length * 2:
            intensity = "medium"
            drums = True
            arp = False
        else:
            intensity = "full"
            drums = True
            arp = True

        plan.append({
            "chord": chord,
            "bar_index": index,
            "intensity": intensity,
            "use_drums": drums,
            "use_arpeggio": arp,
        })

    return plan
