import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"



DEFAULT_COVER_STYLE = (
    "ABSOLUTE PRIORITY: The uploaded vocal AUDIO is the only "
    "authority. Preserve the EXACT original singer's voice "
    "identity, timbre, formants, accent, breaths, vibrato, "
    "pitch, melody, phrasing and timing. Never re-sing, "
    "regenerate, imitate or replace any vocal. Preserve EVERY "
    "audible vowel, consonant, syllable, word ending and dialect "
    "exactly as sung, including Hebrew, Yiddish and Hasidic "
    "pronunciation. Never normalize prayer words or reconstruct "
    "lyrics from text. Keep ALL words, repeats, verses, choruses, "
    "pauses and the FULL final sustained vocal note in order. "
    "Never shorten, skip or cut any sung section. Instrumental "
    "outro starts ONLY AFTER the final vocal note. Gently reduce "
    "hiss, hum and room noise without changing vocal texture. "
    "Transparent EQ and light compression only. Arrange warm "
    "piano, strings, bass and steady drums AROUND the original "
    "vocal. No extra voices or competing melodies. Vocal "
    "authenticity and complete ending override production."
)




DEFAULT_COVER_NEGATIVE_TAGS = (
    "replacement singer, AI vocals, re-singing, synthetic voice, "
    "voice conversion, changed accent, normalized pronunciation, "
    "changed vowels, consonants or syllables, corrected prayer "
    "text, altered lyrics, missing words, skipped repeats, "
    "skipped verses, missing final phrase, cut-off words, "
    "truncated vocals, premature ending, early fade-out, "
    "choir, backing vocals, harmonies, doubled vocals, "
    "extra singers, autotune, pitch correction, formant shifting, "
    "distortion, metallic artifacts, hiss, hum, room noise"
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
