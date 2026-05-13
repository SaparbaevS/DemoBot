import asyncio
import json
import logging
import os
import tempfile
import time

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from config import settings

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

_RETRY_ATTEMPTS = 3
_RETRY_DELAY = 20  # seconds between retries on 503


def _call_with_retry(fn):
    """Retry fn up to _RETRY_ATTEMPTS times on 503 UNAVAILABLE."""
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            return fn()
        except ServerError as e:
            if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < _RETRY_ATTEMPTS:
                logger.warning("Gemini 503 — повтор через %ds (попытка %d/%d)", _RETRY_DELAY, attempt, _RETRY_ATTEMPTS)
                time.sleep(_RETRY_DELAY)
            else:
                raise


# ─── Voice transcription ─────────────────────────────────────────────────────

def _sync_transcribe(audio_bytes: bytes) -> str:
    tmp_path = None
    uploaded = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        uploaded = _client.files.upload(
            file=tmp_path,
            config=types.UploadFileConfig(
                mime_type="audio/ogg",
                display_name="voice_message",
            ),
        )

        def _generate():
            return _client.models.generate_content(
                model=_MODEL,
                contents=[
                    uploaded,
                    (
                        "Transcribe this voice message exactly as spoken. "
                        "Return ONLY the transcribed text — no labels, no formatting."
                    ),
                ],
            )

        response = _call_with_retry(_generate)
        return response.text.strip()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if uploaded:
            try:
                _client.files.delete(name=uploaded.name)
            except Exception:
                pass


async def transcribe_voice(audio_bytes: bytes) -> str:
    return await asyncio.to_thread(_sync_transcribe, audio_bytes)


# ─── Daily activity analysis ─────────────────────────────────────────────────

_ANALYZE_PROMPT = """\
You are a personal activity analyst. Analyze the following daily activity logs
and extract each activity as a structured JSON array.

Each log line has the format: [YYYY-MM-DD HH:MM:SS] <user message>
The timestamp in brackets is the EXACT moment the user sent the message.

Activity logs (in chronological order):
{logs}

Rules:
- Each array item must have exactly these fields:
    "time"     : string  — ALWAYS fill with a time in "HH:MM" format.
                           Priority: (1) time explicitly stated by the user,
                           (2) time from the log timestamp [HH:MM:SS].
                           Never use "—", never leave unknown.
    "activity" : string  — short description in Russian (max 40 chars)
    "duration" : integer | null — duration in MINUTES, calculated automatically:
                           = timestamp of the NEXT activity − timestamp of this activity.
                           If the user explicitly mentions a duration, use that instead.
                           For the LAST activity of the day, use null (end time unknown).
    "category" : one of "сон", "еда", "работа", "отдых", "спорт", "транспорт", "общение", "покупка", "другое"
    "amount"   : number | null — money spent in this activity (in sum/сум).
                           Extract from phrases like "купил за 5000", "заплатил 12000",
                           "потратил 50 000", "стоило 8500". null if no purchase.
- Keep the language consistent with the logs (Russian preferred).
- Return ONLY a valid JSON array, nothing else.
"""


def _sync_analyze(logs_text: str) -> list[dict]:
    prompt = _ANALYZE_PROMPT.format(logs=logs_text)

    def _generate():
        return _client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

    response = _call_with_retry(_generate)
    return json.loads(response.text)


async def analyze_daily_activities(activities: list[dict]) -> list[dict]:
    if not activities:
        return []

    logs_text = "\n".join(
        f"[{a['created_at']}] {a['raw_text']}" for a in activities
    )
    return await asyncio.to_thread(_sync_analyze, logs_text)
