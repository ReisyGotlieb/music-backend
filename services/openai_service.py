
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
You are an audio-first transcription specialist for songs in Hebrew, Yiddish,
English and any other language, including mixed-language and liturgical singing.
Listen to the ENTIRE recording, from the first audible sung sound to the last.

PRIMARY RULE: The actual audible performance is the only authority.
Transcribe what the singer actually pronounces, not conventional spelling,
memorized lyrics, prayer books, biblical texts or expected grammar.
Write ALL sung words in LATIN LETTERS ONLY, using phonetic spelling that best
represents the actual sounds. Preserve audible vowels, consonants, syllables,
diphthongs, endings, stress, dialect, and pronunciation in EACH occurrence.
Accept any Hasidic, Ashkenazi, Litvish, Yerushalmi, Sephardi, Yemenite,
Yiddish, mixed or individual accent without presuming a dialect.
Use KH for an audible guttural Hebrew Chet, not English CH.

CONTEXT: Use linguistic context, authentic Yiddish vocabulary and grammar,
and other repetitions to help identify UNCLEAR words only when supported by
the audio. Never use context to overwrite clearly audible phonemes. Never
reconstruct a familiar prayer or verse from memory. Never insert omitted
words or correct grammar. If a word is truly unintelligible, use [Unclear].
If a repeated word is pronounced differently, preserve each actual occurrence;
do not normalize to the majority pronunciation. Do not invent lyrics.

COMPLETENESS: Include every sung word, identifiable wordless syllable,
phrase, verse, chorus and repetition in original order, including the ending.
For Na, La, Ma, Du, Oy, Ay, Lai etc., write the actual syllables and repeats.
For purely closed-mouth humming without identifiable syllables, lyrics may
be empty. Never infer words from humming. Preserve full repeated passages;
never shorten them to a label alone.

STRUCTURE: Use section labels such as [Verse 1], [Chorus], [Bridge] and
[Verse 1 Repeat] only when supported by musical phrasing and repetition.
Put each sung phrase on its own line and a blank line between sections.
Do not invent instrumental intros, transitions, outros or extra sung sections.
The labels are organizational, not instructions to generate music.

TITLE: Return a short meaningful title, preferably a recognizable sung
phrase; Hebrew script is permitted for the title of Hebrew/Yiddish songs.
For wordless recordings use a neutral title.

OUTPUT: Return ONLY valid JSON with exactly two string fields:
{"title":"","lyrics":""}
No Markdown, explanations or additional fields. Sung lyrics must be in Latin
letters; section labels may be bracketed. Maximum lyrics length is 5000
characters. Never silently truncate or omit content to meet the limit.
Before answering check phonetic fidelity, all repetitions and the last sound.
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
    """Parse and validate the two transcription fields."""

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

    required_fields = ("title", "lyrics")

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
                                "Transcribe this complete song recording "
                                "and return title and lyrics as JSON. "
                                "The recording may contain real words, "
                                "wordless syllables, humming, or a mix. "
                                "Do not invent lyrics for humming. "
                                "Return exactly two JSON string fields. "
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
