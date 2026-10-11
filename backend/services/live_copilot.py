import base64
import json
import os
import re
import wave
from io import BytesIO

import httpx


CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_STT_MODEL = os.getenv(
    "CLOUDFLARE_STT_MODEL",
    "@cf/openai/whisper-large-v3-turbo",
)

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
OLLAMA_CHAT_URL = os.getenv(
    "OLLAMA_CHAT_URL",
    "https://ollama.com/api/chat",
)

AI_TIMEOUT_SECONDS = float(
    os.getenv("AI_TIMEOUT_SECONDS", "45")
)


class ProviderConfigurationError(RuntimeError):
    pass


def pcm16_mono_to_wav(
    pcm: bytes,
    sample_rate: int = 16000,
) -> bytes:
    buffer = BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)

    return buffer.getvalue()


async def transcribe_pcm(
    pcm: bytes,
    language: str = "en",
) -> str:
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        raise ProviderConfigurationError(
            "Configure Cloudflare credentials in .env."
        )

    if not pcm:
        return ""

    audio_wav = pcm16_mono_to_wav(pcm)
    audio_b64 = base64.b64encode(audio_wav).decode("ascii")

    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/"
        f"{CLOUDFLARE_STT_MODEL}"
    )

    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "audio": audio_b64,
        "task": "transcribe",
        "language": language,
        "vad_filter": True,
    }

    async with httpx.AsyncClient(
        timeout=AI_TIMEOUT_SECONDS
    ) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    result = body.get("result") or {}
    text = result.get("text", "")

    return text.strip() if isinstance(text, str) else ""


async def detect_question_and_draft_answer(
    transcript: str,
    topics: list[str],
    course: str,
    target_role: str | None,
    difficulty: str,
    recent_context: list[dict[str, str]],
) -> dict:
    if not OLLAMA_API_KEY:
        raise ProviderConfigurationError(
            "Configure OLLAMA_API_KEY in .env."
        )

    system_prompt = """
You are a conversational assistant for interview practice.
The transcript may contain a question, an answer, or background speech.

Use the recent context to determine whether the latest transcript contains
a question or prompt that the user should respond to.

Return should_respond=false for ordinary statements, incomplete speech,
background conversation, or when no clear question is present.

If a clear interview question is present, provide a concise, accurate,
natural answer suitable for interview practice.

Return ONLY valid JSON with:
{
  "should_respond": true or false,
  "question": "detected question or empty string",
  "answer": "suggested answer or empty string"
}
"""

    context_text = "\n".join(
        f'{item["role"]}: {item["content"]}'
        for item in recent_context[-8:]
    )

    user_prompt = (
        f"Course: {course}\n"
        f"Target role: {target_role or 'Not specified'}\n"
        f"Topics: {', '.join(topics)}\n"
        f"Difficulty: {difficulty}\n"
        f"Recent context:\n{context_text or '(none)'}\n\n"
        f"Latest transcript:\n{transcript}"
    )

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "options": {
            "temperature": 0.2,
        },
    }

    async with httpx.AsyncClient(
        timeout=AI_TIMEOUT_SECONDS
    ) as client:
        response = await client.post(
            OLLAMA_CHAT_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    content = body.get("message", {}).get("content", "")

    try:
        result = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {
            "should_respond": False,
            "question": "",
            "answer": "",
        }

    question = result.get("question", "")
    answer = result.get("answer", "")

    if not isinstance(question, str) or not isinstance(answer, str):
        return {
            "should_respond": False,
            "question": "",
            "answer": "",
        }

    answer = re.sub(r"\s+", " ", answer).strip()

    return {
        "should_respond": (
            result.get("should_respond") is True
            and bool(answer)
        ),
        "question": question.strip(),
        "answer": answer,
    }