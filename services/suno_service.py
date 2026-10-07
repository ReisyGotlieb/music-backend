import os
import httpx


SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE_URL = "https://apibox.erweima.ai"


async def add_instrumental(
    upload_url: str,
    title: str = "My Song",
    tags: str = (
    "professional studio accompaniment, "
    "strict accompaniment to the uploaded vocal performance, "
    "preserve the exact timing, tempo, meter and phrase boundaries of the source audio, "
    "preserve the harmonic context implied by the source vocal, "
    "follow every pause, entrance, phrase length and structural section, "
    "do not reinterpret or rewrite the source performance, "
    "do not change tempo between sections, "
    "do not add or remove measures, "
    "accompany the complete source audio from beginning to end, "
    "supportive piano, warm strings, bass, subtle drums, "
    "leave space for the original lead vocal"
),
    negative_tags: str = (
    "tempo changes, rubato reinterpretation, "
    "key changes, modulation, reharmonization, "
    "melody rewriting, lead melody doubling, "
    "instrumental melody copying the vocal, "
    "added measures, removed measures, "
    "intro extension, outro extension, "
    "early ending, shortened structure, omitted phrases, "
    "busy countermelody, dense orchestration, "
    "solo instruments, choir, backing vocals, "
    "vocal harmonies, second voice, vocal ad-libs"
),
):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

    url = f"{SUNO_BASE_URL}/api/v1/generate/add-instrumental"

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "uploadUrl": upload_url,
        "title": title,
        "tags": tags,
        "negativeTags": negative_tags,

        # זמני בשלב ה-POC.
        # בהמשך נחליף ל-callback endpoint אמיתי אצלנו.
        "callBackUrl": "https://example.com/callback",

        "model": "V6",

        # שומרים על הנאמנות הגבוהה למקור
        "audioWeight": 1.0,

        # בניסוי הקודם 0.5 נתן תוצאה מדויקת ומסודרת יותר
        "styleWeight": 0.5,

        # כרגע לא מוסיפים יצירתיות חריגה
        "weirdnessConstraint": 0.0,

        # כרגע משאירים קבוע כדי לא לשנות כמה משתנים יחד
        "variety": 0,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

    response.raise_for_status()
    return response.json()


async def get_generation_details(task_id: str):
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY is not configured")

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
    return response.json()
