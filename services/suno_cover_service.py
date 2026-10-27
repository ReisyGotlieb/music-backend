
import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


DEFAULT_COVER_STYLE = (
    "ABSOLUTE PRIORITY: Preserve the EXACT ORIGINAL uploaded "
    "lead vocal recording and singer's UNIQUE VOCAL FINGERPRINT. "
    "Keep 100% of the original voice identity, timbre, formants, "
    "resonance, texture, accent, pronunciation, vibrato, breaths, "
    "emotion, melody, lyrics, phrasing and timing. "
    "NEVER regenerate, replace, imitate, resynthesize or re-sing "
    "the voice. Use the AUTHENTIC ORIGINAL vocal audio unchanged. "
    "Preserve every note, syllable, pause and natural imperfection. "
    "NO pitch correction, autotune, formant shifting or time stretching. "
    "Build rich professional piano, strings, bass and rhythmic "
    "drums AROUND the vocal, following its exact timing and melody. "
    "Original lead vocal always dominant. No additional voices. "
    "Use only transparent minimal mixing. "
    "Keep EVERY original word, phrase, verse, chorus and final note. "
    "Never omit, shorten, replace or truncate any sung passage. "
    "Optional instrumental intro and outro must not replace vocals. "
    "End naturally AFTER the complete final vocal phrase. "
    "VOCAL AUTHENTICITY OVERRIDES ALL PRODUCTION ENHANCEMENTS."
)


DEFAULT_COVER_NEGATIVE_TAGS = (
    "instrumental only, missing vocals, replacement singer, "
    "altered voice, synthetic vocals, re-sung vocals, "
    "autotune, pitch correction, robotic voice, "
    "backing vocals, choir, vocal harmonies, doubled vocals, "
    "vocal ad-libs, changed melody, changed phrasing, "
    "missing lyrics, missing phrases, skipped verses, "
    "competing melodies, instruments doubling lead vocal, "
    "heavy drums, distorted vocals, abrupt ending, "
    "truncated ending, premature ending, cut-off vocals, "
    "cut-off words, unfinished phrases, early fade-out"
)


def _callback_url():
    return (
        os.getenv("SUNO_CALLBACK_URL")
        or "https://example.com/callback"
    )


def _validate(
    title: str,
    style: str,
    negative_tags: str,
    lyrics: str,
):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")

    for name, value, limit in (
        ("style", style, 1000),
        ("negative_tags", negative_tags, 500),
        ("lyrics", lyrics, 5000),
    ):
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")

        if len(value) > limit:
            raise ValueError(
                f"{name} exceeds Suno limit: "
                f"{len(value)}/{limit} characters"
            )


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
        raise RuntimeError(
            "SUNO_API_KEY is not configured"
        )

    _validate(
        title,
        style,
        negative_tags,
        lyrics,
    )

    url = f"{SUNO_BASE_URL}/api/v1/generate/upload-cover"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "uploadUrl": upload_url,
        "title": title,
        "style": style,
        "negativeTags": negative_tags,
        "instrumental": False,
        "callBackUrl": _callback_url(),
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
            url,
            headers=headers,
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
        raise RuntimeError(
            "SUNO_API_KEY is not configured"
        )

    url = f"{SUNO_BASE_URL}/api/v1/generate/record-info"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
    }

    params = {
        "taskId": task_id
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            url,
            headers=headers,
            params=params,
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
