
import os
import httpx

SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"

DEFAULT_TAGS = (
    "ABSOLUTE PRIORITY: Use the EXACT original uploaded lead vocal audio "
    "as the sole lead vocal. Preserve unique voice identity, timbre, "
    "formants, accent, pronunciation, pitch, vibrato, breaths, emotion, "
    "melody, lyrics, phrasing, entrances, pauses and timing. Keep every "
    "sung word, verse, chorus and final note in full and in order. "
    "Never re-sing, regenerate or replace the voice. Arrange warm piano, "
    "strings, bass and steady rhythmic drums around the vocal. Keep it "
    "clear and dominant, with only transparent minimal mixing. Optional "
    "instrumental intro, transitions and outro must not displace singing. "
    "Finish AFTER the complete final vocal phrase, never mid-word. "
    "VOCAL AUTHENTICITY OVERRIDES PRODUCTION."
)

DEFAULT_NEGATIVE_TAGS = (
    "AI vocals, regenerated voice, re-sung vocals, replacement singer, "
    "voice conversion, synthetic vocals, autotune, pitch correction, "
    "formant shifting, time stretching, altered pronunciation, changed "
    "lyrics, missing words, skipped verses, choir, backing vocals, "
    "harmonies, doubled vocals, extra singers, vocal effects, instruments "
    "doubling lead melody, overpowering instruments, aggressive denoising, "
    "instrumental replacement of vocals, cut-off words, truncated ending, "
    "premature ending, early fade-out"
)

DEFAULT_INSTRUMENTAL_STYLE = (
    "Professional instrumental accompaniment, warm piano, expressive "
    "strings, bass and gentle rhythmic drums, following the uploaded "
    "melody and timing. No competing lead melody. Preserve the complete "
    "song structure and natural ending."
)

DEFAULT_INSTRUMENTAL_NEGATIVE_TAGS = (
    "vocals, lead singer, backing vocals, choir, harmonies, second voice, "
    "doubled vocals, busy countermelody, instruments doubling the vocal "
    "melody, heavy drums, truncated ending"
)


def _check_length(name: str, value: str, limit: int):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(
            f"{name} exceeds Suno limit or is invalid: "
            f"{len(value) if isinstance(value, str) else 'invalid'}/{limit}"
        )


def _callback_url():
    return os.getenv(
        "SUNO_CALLBACK_URL",
        "https://example.com/callback"
    )

    if not url:
        raise RuntimeError(
            "SUNO_CALLBACK_URL is not configured"
        )

    return url


async def _post(endpoint: str, payload: dict):
    if not SUNO_API_KEY:
        raise RuntimeError(
            "SUNO_API_KEY is not configured"
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{SUNO_BASE_URL}{endpoint}",
            headers={
                "Authorization": f"Bearer {SUNO_API_KEY}"
            },
            json=payload,
        )

    response.raise_for_status()
    result = response.json()

    if result.get("code") != 200:
        raise RuntimeError(
            f"Suno generation failed: {result}"
        )

    return result


async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = DEFAULT_TAGS,
    negative_tags: str = DEFAULT_NEGATIVE_TAGS,
    lyrics: str | None = None,
):
    _check_length("tags", tags, 1000)
    _check_length("negative_tags", negative_tags, 500)

    if lyrics is not None:
        _check_length("lyrics", lyrics, 5000)

    payload = {
        "uploadUrl": upload_url,
        "title": title,
        "tags": tags,
        "negativeTags": negative_tags,
        "callBackUrl": _callback_url(),
        "model": "V6",
        "audioWeight": 1.0,
        "styleWeight": 0.3,
        "weirdnessConstraint": 0.0,
        "variety": 0,
    }

    if lyrics and lyrics.strip():
        payload["lyrics"] = lyrics

    return await _post(
        "/api/v1/generate/add-instrumental",
        payload
    )


async def get_generation_details(task_id: str):
    if not SUNO_API_KEY:
        raise RuntimeError(
            "SUNO_API_KEY is not configured"
        )

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
            f"Suno status request failed: {result}"
        )

    return result


async def upload_cover(
    upload_url: str,
    title: str = "My Song Cover",
    style: str = DEFAULT_INSTRUMENTAL_STYLE,
):
    _check_length("style", style, 1000)
    _check_length(
        "negative_tags",
        DEFAULT_INSTRUMENTAL_NEGATIVE_TAGS,
        500
    )

    payload = {
        "uploadUrl": upload_url,
        "title": title,
        "style": style,
        "negativeTags": DEFAULT_INSTRUMENTAL_NEGATIVE_TAGS,
        "instrumental": True,
        "model": "V6",
        "callBackUrl": _callback_url(),
        "audioWeight": 1.0,
        "styleWeight": 0.5,
        "weirdnessConstraint": 0.0,
        "variety": 0,
    }

    return await _post(
        "/api/v1/generate/upload-cover",
        payload
    )
