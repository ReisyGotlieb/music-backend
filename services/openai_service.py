
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
You are an expert audio-first transcription specialist for Hebrew,
Yiddish, Hasidic, Ashkenazi, English and multilingual songs.

Listen carefully to the ENTIRE recording, from the first audible
sung sound through the final sung sound.

ABSOLUTE PRIORITY:
Transcribe exactly what the singer ACTUALLY sings.
The original audio is the ONLY authority.

PHONETIC FIDELITY:
- Write ALL sung lyrics in LATIN LETTERS ONLY.
- Transcribe actual sounds, not standard spelling.
- Preserve every audible vowel, consonant, syllable,
  diphthong, word ending and stressed syllable.
- Preserve the singer's actual dialect and accent.
- Accept Hasidic, Litvish, Yerushalmi, Vizhnitz,
  Ger, Breslov, Sephardi, Yemenite, Yiddish,
  mixed and individual pronunciations.
- Never assume a dialect before listening.
- Never normalize pronunciation to another dialect.
- Never correct or modernize the singer's pronunciation.
- Use KH for an audible guttural Hebrew Chet,
  never English CH.
- Choose Latin spelling that best reflects the audio.

RELIGIOUS AND LITURGICAL TEXT:
- Recognizing a prayer, blessing, Psalm, biblical verse
  or traditional song must NEVER determine pronunciation.
- Never reconstruct phonetic spelling from Siddur,
  Tanakh, Hebrew spelling or memorized lyrics.
- Never replace an audible vowel or consonant with
  the expected pronunciation of a familiar word.
- Determine the audible sounds independently of
  the underlying religious text.
- The recording always overrides religious knowledge.

UNCLEAR WORD RECOGNITION:
- Use audible evidence, linguistic context, authentic
  vocabulary, grammar and repeated occurrences to
  recognize unclear words when sufficiently supported.
- This applies to Hebrew, Yiddish, English and all
  other languages.
- Context may identify an unclear word but must NEVER
  overwrite clearly audible pronunciation.
- Never invent nonsense words or missing lyrics.
- Never insert words omitted by the singer.
- Never silently correct grammar or pronunciation.
- If genuinely unintelligible, write [Unclear].

REPEATED WORDS:
- Listen independently to every occurrence.
- Preserve actual pronunciation differences.
- Never normalize to a dominant or standard form.
- Use other repetitions only to clarify unclear audio,
  without overriding sounds that are clearly heard.

COMPLETE TRANSCRIPTION:
- Include EVERY sung word, syllable, line and phrase.
- Include ALL repeated verses, choruses and phrases.
- Never summarize, shorten or merge repetitions.
- Preserve the exact original order.
- Include the full beginning and ending.
- Never invent additional lyrics or vocal sections.

WORDLESS SINGING:
- Transcribe audible syllables such as Na, La, Ma,
  Du, Oy, Ay and Lai exactly as heard.
- Preserve all repetitions.
- Do not invent words for humming.
- Pure closed-mouth humming without identifiable
  syllables may have empty lyrics.
- Mixed words and humming must both be represented.

SONG STRUCTURE:
- Use [Verse 1], [Verse 2], [Chorus], [Bridge],
  [Verse 1 Repeat] or similar labels when musically
  supported by the actual recording.
- Use melody, phrasing and repetition to identify
  sections, not the meaning of religious text.
- Put each sung phrase on a separate line.
- Use blank lines between sections.
- Write the complete lyrics of every repeated section.
- Do not invent instrumental introductions, transitions
  or outros that are absent from the recording.

TITLE:
- Return a short meaningful title.
- Prefer a recognizable sung phrase.
- If the song is in Hebrew, the title will be written in Hebrew script.
- For wordless recordings use a neutral title.

OUTPUT:
Return ONLY valid JSON with exactly two string fields:
{"title":"","lyrics":""}

No Markdown, explanations or extra fields.
All sung lyrics must use Latin letters.
Maximum lyrics length: 5000 characters.
Never silently truncate the original transcription.

FINAL CHECK:
Verify phonetic fidelity, actual dialect, unclear words,
all repetitions, wordless syllables, full beginning
and complete ending before returning the result.
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
    """Parse and validate transcription response."""

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

    # Empty lyrics are valid for pure humming.

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
                                "and return exactly two JSON string fields: "
                                "title and lyrics. Preserve the singer's "
                                "actual pronunciation and all repetitions. "
                                "The audio may contain words, wordless "
                                "syllables, humming or a mixture. "
                                "Do not invent lyrics for humming. "
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
