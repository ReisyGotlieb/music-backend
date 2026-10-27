
import os
import json
import base64
import asyncio
import tempfile
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx


logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-audio")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

MAX_AUDIO_BYTES = 20 * 1024 * 1024
MAX_ATTEMPTS = 2


SYSTEM_PROMPT = """
You are an expert audio/music transcription specialist for Hasidic, Ashkenazi, Hebrew, Yiddish, English and multilingual songs, including Jewish liturgical singing. Listen to the COMPLETE recording, first sung sound through last. Produce exactly four Suno fields: title, lyrics, tags, negative_tags. The audio is the authority.

TRANSCRIPTION MODES — SELECT PER PASSAGE, NEVER OUTPUT THE MODE:
A — GENERAL: Ordinary songs in any language, including mixed languages. A Hasidic singer or religious theme alone does not imply B. Recognize unclear words using audible evidence plus vocabulary, authentic Yiddish grammar, syntax, repetition and linguistic context (also for Hebrew, English and other languages). Correct an obvious accidental omission only when strongly supported by other occurrences and context; never fabricate words or force a conventional dialect. Preserve the singer's actual accent, vowels and consonants, including Hasidic rather than Litvish pronunciation.
B — STRICT LITURGICAL PHONETICS: Recognizable prayers, blessings, Psalms, biblical verses and traditional liturgical texts, even within modern songs. Transcribe the SOUNDS actually sung, never a reconstructed or standardized religious text. Determine audible phonemes BEFORE identifying a familiar prayer. Familiarity with Siddur, Tanakh, Psalms, grammar, spelling, meaning, dictionaries or memorized lyrics may identify the underlying word but MUST NEVER supply, correct or decide its phonetic spelling, vowels (A/O/E/I/U), consonants, endings or stress. Preserve every audible vowel, consonant, syllable, diphthong, word ending, stress, unusual pronunciation and accent. Accept Sephardi, Yemenite, Litvish, Yerushalmi, Vizhnitz, Ger, Breslov, other Hasidic, mixed and individual dialects without assuming or normalizing any. Never translate, modernize, reinterpret, replace or silently correct. If genuinely unintelligible, write [Unclear], not a guessed religious word. B overrides conflicting A/context rules except the shared dominant-pronunciation rule.
Examples ONLY if actually heard: Lefonecho (not Lefanecha); Eloykai (not Elohai); Osiso (not Asita); Nishmo (not Nishma); Le'akhriseykh (not Le'akh risekh); Vekhi (not Bekhi). Never assume these pronunciations.

SHARED PHONETIC RULES:
Write all SUNG words in LATIN LETTERS ONLY, choosing spelling that reflects the audible pronunciation; use KH for guttural Hebrew Chet, not English CH (e.g., Tapukhei if the sound is guttural). Independently listen to EVERY occurrence of a repeated word first. If one AUDIO-BASED pronunciation clearly dominates, use it consistently for that SAME word (e.g., four Lefonecho and one Lefonechu -> five Lefonecho); if no clear dominant form, preserve each occurrence as heard. Never use standard spelling, grammar, religious knowledge or merely similar words to determine dominance. This is the ONLY permitted pronunciation normalization in B.

WORDLESS SINGING / HUMMING:
Transcribe all identifiable syllables (Na, La, Ma, Du, Oy, Ay, Lai, etc.) and repetitions exactly. Do not invent meaningful lyrics or mark audible singing as instrumental. For pure closed-mouth humming with no identifiable syllables, lyrics may be an empty string; the uploaded melody and timing remain the reference for accompaniment. Mixed singing and humming are valid.

COMPLETENESS AND STRUCTURE:
Include EVERY sung word, syllable, phrase, verse, chorus and repetition in original order, including the full beginning, ending, sustained notes and vocal entrances/pauses. Never summarize, merge, omit, replace, truncate or invent sung content; only the explicit dominant-pronunciation rule and Mode A's strongly supported accidental-omission correction are exceptions. Identify musical sections from actual melody, phrasing and repetition, not the religious meaning. Use supported Suno labels such as [Verse 1], [Verse 2], [Chorus], [Bridge], [Verse 1 Repeat], [Chorus Repeat]; use [Chorus] for a musically supported repeated refrain and a neutral verse label if uncertain. Write each sung phrase on a separate line, blank line between sections, and FULL lyrics for every repeat. Use [Instrumental Break] only for genuinely instrumental passages; never invent sections or transitions.

ARRANGEMENT:
Choose tasteful instrumental intro, transitions or outro only if musically beneficial; omit uncertain additions. Intro may precede the first original vocal, outro may follow the last, and transitions may occur only BETWEEN complete original vocal phrases. Represent additions with Suno section labels when useful. Never displace, interrupt, replace or cut any original singing or sustained ending, or invent sung lyrics for instrumental sections. For humming/wordless singing, follow the exact original melody and timing.

TITLE:
Short, meaningful and preferably a recognizable sung phrase; prefer Hebrew script for Hebrew/Yiddish songs, a neutral short title for wordless recordings; never unrelated or invented.

TAGS:
Write concise professional Suno arrangement instructions: use the EXACT ORIGINAL uploaded lead-vocal AUDIO, preserving singer identity, timbre, formants, resonance, accent, pronunciation, pitch, melody, phrasing, vibrato, breaths, emotion, entrances, pauses and timing; never regenerate, imitate, replace or re-sing. Build a rich supportive arrangement with piano, warm strings, bass and rhythmic drums around the voice, keeping it clear and dominant. Preserve every vocal phrase and final note; include tasteful instrumental intro/transition/outro only if appropriate. For humming, accompany the original hummed melody/timing. VOCAL AUTHENTICITY OVERRIDES PRODUCTION.

NEGATIVE_TAGS:
Exclude AI/replacement/synthetic/re-sung vocals, voice conversion, autotune, pitch correction, formant shifting, time stretching, altered pronunciation/lyrics/melody, missing words/verses, choir, backing vocals, harmonies, doubling, extra singers, instrumental replacement of vocals, overpowering instruments, aggressive vocal processing, truncated phrases, abrupt/cut-off endings, and invented lyrics for wordless recordings.

LIMITS AND OUTPUT:
Return ONLY valid JSON with exactly four STRING fields: {"title":"","lyrics":"","tags":"","negative_tags":""}. No Markdown, code fences, explanations, translations, mode labels or extra fields. Lyrics: Latin letters for sung words, Suno bracketed section labels, line breaks and blank lines, complete repeats. Pure humming may have empty lyrics. Limits: tags <=1000 characters; negative_tags <=500; lyrics <=5000. NEVER silently delete original sung content to fit a limit; if full lyrics exceed 5000, do not pretend the output is complete or silently truncate it.

FINAL CHECK BEFORE OUTPUT:
Correct mode for each passage; Mode A contextual word recognition without invention; Mode B exact audio-first dialect/pronunciation without liturgical reconstruction; dominant form determined only by audio; all sung syllables and repetitions, wordless sections, musical structure, first and last vocal notes retained; no vocal replacement or cut ending; four strings, valid JSON and character limits. The complete original performance takes priority.
"""


async def convert_audio_to_wav(audio_bytes: bytes) -> bytes:
    """Convert browser audio formats to 24 kHz mono WAV."""

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "input_audio"
        output_path = Path(temp_dir) / "output.wav"

        input_path.write_bytes(audio_bytes)

        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-nostdin",
                "-y",
                "-i", str(input_path),
                "-vn",
                "-ac", "1",
                "-ar", "24000",
                "-c:a", "pcm_s16le",
                str(output_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "FFmpeg is not installed on the server"
            ) from exc

        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=90,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise ValueError(
                "Audio conversion timed out"
            ) from exc

        if process.returncode != 0 or not output_path.exists():
            details = stderr.decode(
                "utf-8",
                errors="replace",
            )[:500]
            raise ValueError(
                f"Audio conversion failed: {details}"
            )

        wav_bytes = output_path.read_bytes()

        if len(wav_bytes) > MAX_AUDIO_BYTES:
            raise ValueError(
                "Converted WAV exceeds 20 MB limit"
            )

        return wav_bytes


def parse_song_response(result: dict) -> dict:
    """Parse and validate the four required GPT fields."""

    choices = result.get("choices") or []

    if not choices:
        raise ValueError("OpenAI returned no choices")

    choice = choices[0]
    finish_reason = choice.get("finish_reason")

    if finish_reason == "length":
        raise ValueError(
            "OpenAI response was truncated"
        )

    if finish_reason not in (None, "stop"):
        raise ValueError(
            f"OpenAI finished unexpectedly: {finish_reason}"
        )

    message = choice.get("message") or {}
    content = message.get("content")

    if not isinstance(content, str):
        raise ValueError(
            "OpenAI returned no text content"
        )

    content = content.strip()

    if content.startswith("```"):
        parts = content.split("\n", 1)

        if len(parts) == 2:
            content = parts[1].rsplit(
                "```", 1
            )[0].strip()

    try:
        song = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "OpenAI returned invalid JSON"
        ) from exc

    if not isinstance(song, dict):
        raise ValueError(
            "OpenAI JSON must be an object"
        )

    required_fields = (
        "title",
        "lyrics",
        "tags",
        "negative_tags",
    )

    for field in required_fields:
        if not isinstance(song.get(field), str):
            raise ValueError(
                f"OpenAI response missing valid field: {field}"
            )

    if not song["title"].strip():
        song["title"] = "My Melody"

    # IMPORTANT:
    # Empty lyrics are valid for pure humming.
    # Do not reject them.

    if len(song["lyrics"]) > 5000:
        raise ValueError(
            "Lyrics exceed 5000 characters"
        )

    if len(song["tags"]) > 1000:
        raise ValueError(
            "Tags exceed 1000 characters"
        )

    if len(song["negative_tags"]) > 500:
        raise ValueError(
            "Negative tags exceed 500 characters"
        )

    return {
        field: song[field]
        for field in required_fields
    }


async def analyze_song(upload_url: str) -> dict:

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured"
        )

    parsed = urlparse(upload_url)

    if parsed.scheme != "https":
        raise ValueError(
            "upload_url must use HTTPS"
        )

    allowed_host = os.getenv("AUDIO_PUBLIC_HOST")

    if not allowed_host:
        raise RuntimeError(
            "AUDIO_PUBLIC_HOST is not configured"
        )

    if parsed.hostname != allowed_host:
        raise ValueError(
            "Audio URL host is not allowed"
        )

    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=False,
    ) as client:

        response = await client.get(upload_url)
        response.raise_for_status()

        audio_bytes = response.content

        if len(audio_bytes) > MAX_AUDIO_BYTES:
            raise ValueError(
                "Audio file exceeds 20 MB limit"
            )

        audio_bytes = await convert_audio_to_wav(
            audio_bytes
        )

        audio_base64 = base64.b64encode(
            audio_bytes
        ).decode("utf-8")

        payload = {
            "model": OPENAI_MODEL,
            "modalities": ["text"],
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyze this complete song recording "
                                "and return the Suno-ready JSON. "
                                "The recording may contain real words, "
                                "wordless syllables, humming, or a mix. "
                                "Do not invent lyrics for humming. "
                                "Return all four JSON string fields. "
                                "Empty lyrics are valid for pure humming."
                            ),
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "wav",
                            },
                        },
                    ],
                },
            ],
        }

        last_error = None

        for attempt in range(1, MAX_ATTEMPTS + 1):

            try:
                api_response = await client.post(
                    OPENAI_URL,
                    headers={
                        "Authorization": (
                            f"Bearer {OPENAI_API_KEY}"
                        ),
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=240.0,
                )

                api_response.raise_for_status()

                result = api_response.json()

                return parse_song_response(result)

            except ValueError as exc:
                last_error = exc

                logger.warning(
                    "OpenAI transcription validation failed "
                    "on attempt %s/%s: %s",
                    attempt,
                    MAX_ATTEMPTS,
                    str(exc),
                )

                if attempt < MAX_ATTEMPTS:
                    continue

    raise RuntimeError(
        "OpenAI could not return a valid song analysis "
        f"after {MAX_ATTEMPTS} attempts: {last_error}"
    )
