
import os
import httpx

SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"

DEFAULT_COVER_STYLE = (
    "ABSOLUTE PRIORITY: Preserve the EXACT ORIGINAL uploaded lead vocal "
    "recording, unique voice identity, timbre, formants, resonance, accent, "
    "pronunciation, pitch, melody, vibrato, breaths, emotion, phrasing and "
    "timing. Never regenerate, replace, imitate, resynthesize or re-sing. "
    "Keep EVERY original word, phrase, verse, chorus and final sustained "
    "note, in full and in order. Build a rich supporting arrangement with "
    "piano, warm strings, bass and steady rhythmic drums around the voice. "
    "Keep the lead vocal dominant; no other voices or melody doubling. "
    "Only minimal transparent EQ and compression. Optional instrumental "
    "intro and outro must not replace vocals. End naturally AFTER the full "
    "last vocal phrase, never mid-word or mid-phrase. VOCAL AUTHENTICITY "
    "OVERRIDES PRODUCTION."
)

DEFAULT_COVER_NEGATIVE_TAGS = (
    "instrumental only, missing vocals, replacement singer, synthetic "
    "vocals, re-sung vocals, voice conversion, autotune, pitch correction, "
    "formant shifting, altered pronunciation, changed melody, changed "
    "phrasing, missing lyrics, skipped verses, choir, backing vocals, "
    "harmonies, doubled vocals, extra singers, vocal ad-libs, competing "
    "melodies, instruments doubling vocals, heavy drums, distorted vocals, "
    "abrupt ending, truncated ending, premature ending, cut-off words, "
    "early fade-out"
)


def _validate(title: str, style: str, negative_tags: str, lyrics: str) -> None:
    for name, value, limit in (
        ("style", style, 1000),
        ("negative_tags", negative_tags, 500),
        ("lyrics", lyrics, 5000),
    ):
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError(
                f"{name} exceeds limit or is not a string: "
                f"{len(value) if isinstance(value, str) else 'invalid'}/{limit}"
            )

    if not title.strip():
        raise ValueError("title must not be empty")


async def generate_upload_cover(
    upload_url: str,
    title: str = "My Song",
    style: str = DEFAULT_COVER_STYLE,
    negative_tags: str = DEFAULT_COVER_NEGATIVE_TAGS,
    lyrics: str = "",
    persona_id: str | None = None,
    persona_model: str = "voice_persona",
):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    _validate(title, style, negative_tags, lyrics)

   callback_url = os.getenv(
    "SUNO_CALLBACK_URL",
    "https://example.com/callback"
)

    if not callback_url:
        raise RuntimeError("SUNO_CALLBACK_URL is not configured")

    payload = {
        "uploadUrl": upload_url,
        "title": title,
        "style": style,
        "negativeTags": negative_tags,
        "instrumental": False,
        "callBackUrl": callback_url,
        "model": "V6",
        "audioWeight": 1.0,
        "styleWeight": 0.0,
        "weirdnessConstraint": 0.0,
        "variety": 0,
    }

    if lyrics.strip():
        payload["lyrics"] = lyrics.strip()

    if persona_id:
        payload["personaId"] = persona_id
        payload["personaModel"] = persona_model

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{SUNO_BASE_URL}/api/v1/generate/upload-cover",
            headers={
                "Authorization": f"Bearer {SUNO_API_KEY}"
            },
            json=payload,
        )

    response.raise_for_status()
    result = response.json()

    if result.get("code") != 200:
        raise RuntimeError(
            f"Suno Cover generation failed: {result}"
        )

    return result


async def get_cover_generation_details(task_id: str):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{SUNO_BASE_URL}/api/v1/generate/record-info",
            headers={
                "Authorization": f"Bearer {SUNO_API_KEY}"
            },
            params={"taskId": task_id},
        )

    response.raise_for_status()
    result = response.json()

    if result.get("code") != 200:
        raise RuntimeError(
            f"Suno Cover status request failed: {result}"
        )

    return result


async def upload_cover(
    upload_url: str,
    title: str = "POC Cover",
    style: str = DEFAULT_COVER_STYLE,
):
    return await generate_upload_cover(
        upload_url=upload_url,
        title=title,
        style=style,
    )
