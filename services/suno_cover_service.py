import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


DEFAULT_COVER_STYLE = (
    "ABSOLUTE PRIORITY: Preserve the EXACT ORIGINAL uploaded "
    "lead vocal and singer's UNIQUE VOCAL FINGERPRINT: identity, "
    "timbre, formants, resonance, accent, pronunciation, pitch, "
    "vibrato, breaths, emotion, melody, phrasing and timing. "
    "Never regenerate, imitate, replace or re-sing the voice. "
    "Gently remove background hiss, hum, room noise and unwanted "
    "artifacts. Improve vocal clarity with transparent studio EQ "
    "and light compression, without changing vocal character. "
    "Preserve natural texture, imperfections and expression. "
    "Build rich professional piano, warm strings, bass and steady "
    "rhythmic drums around the vocal, following its exact timing. "
    "Keep the original singer clear, natural and dominant. "
    "No additional voices or competing melodies. "
    "Keep EVERY word, repetition, verse, chorus and final note. "
    "Never shorten or truncate vocals. Optional intro and outro "
    "must not replace singing. End after the COMPLETE final phrase. "
    "VOCAL AUTHENTICITY OVERRIDES PRODUCTION."
)


DEFAULT_COVER_NEGATIVE_TAGS = (
    "instrumental only, missing vocals, replacement singer, "
    "AI vocals, re-sung vocals, synthetic voice, changed timbre, "
    "altered formants, autotune, pitch correction, robotic voice, "
    "changed accent, pronunciation or melody, missing lyrics, "
    "skipped verses, choir, backing vocals, harmonies, doubled "
    "vocals, extra singers, competing melodies, heavy drums, "
    "distortion, metallic artifacts, aggressive denoising, "
    "background hiss, hum, room noise, abrupt ending, "
    "truncated vocals, cut-off words, early fade-out"
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
        raise RuntimeError("SUNO_API_KEY is not configured")

    _validate(title, style, negative_tags, lyrics)

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
        raise RuntimeError("SUNO_API_KEY is not configured")

    url = f"{SUNO_BASE_URL}/api/v1/generate/record-info"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
    }

    params = {"taskId": task_id}

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
