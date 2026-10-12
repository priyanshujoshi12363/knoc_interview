import base64
import json
import os
import re
import wave
from io import BytesIO

import httpx
from dotenv import load_dotenv

load_dotenv()

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

AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "45"))

NIGIX_TTS_URL = os.getenv(
    "NIGIX_TTS_URL",
    "https://priyanshu00w-nigixmosha.hf.space",
)
NIGIX_TTS_TOKEN = os.getenv("NIGIX_TTS_TOKEN", "")


class ProviderConfigurationError(RuntimeError):
    pass


def pcm16_mono_to_wav(pcm: bytes, sample_rate: int = 16000) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)
    return buffer.getvalue()


async def transcribe_pcm(pcm: bytes, language: str = "en") -> str:
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

    async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()

    result = body.get("result") or {}
    text = result.get("text", "")

    return text.strip() if isinstance(text, str) else ""


async def synthesize_speech(
    text: str,
    language: str = "en",
    voice: str | None = None,
    speed: float = 1.0,
) -> bytes:
    if not NIGIX_TTS_URL or not NIGIX_TTS_TOKEN:
        raise ProviderConfigurationError(
            "Configure NIGIX_TTS_URL and NIGIX_TTS_TOKEN in .env."
        )

    if not text.strip():
        return b""

    url = NIGIX_TTS_URL.rstrip("/") + "/v1/audio/speech"

    headers = {
        "x-api-key": NIGIX_TTS_TOKEN,
        "Content-Type": "application/json",
    }

    payload: dict = {
        "input": text,
        "response_format": "wav",
        "speed": speed,
        "language": language if language in ("en", "hi") else "en",
    }

    if voice:
        payload["voice"] = voice

    async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    return response.content


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
You are a silent interview co-pilot listening to a live job interview.
The transcript may contain a question, an answer, or background speech.

Use the recent context to determine whether the latest transcript contains
a question or prompt that the candidate should respond to.

Return should_respond=false for ordinary statements, incomplete speech,
background conversation, or when no clear question is present.

If a clear interview question is present, provide a concise, accurate,
natural answer the candidate can glance at and paraphrase.

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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "options": {"temperature": 0.2},
    }

    async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
        response = await client.post(
            OLLAMA_CHAT_URL, headers=headers, json=payload
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
            result.get("should_respond") is True and bool(answer)
        ),
        "question": question.strip(),
        "answer": answer,
    }


async def analyze_interview_chunk(
    *,
    pcm: bytes,
    language: str = "en",
    course: str = "General",
    target_role: str | None = None,
    difficulty: str = "intermediate",
    topics: list[str] | None = None,
    recent_context: list[dict[str, str]] | None = None,
) -> dict:
    transcript = await transcribe_pcm(pcm, language=language)

    if not transcript.strip():
        return {
            "transcript": "",
            "should_respond": False,
            "question": "",
            "answer": "",
        }

    result = await detect_question_and_draft_answer(
        transcript=transcript,
        topics=topics or [course],
        course=course,
        target_role=target_role,
        difficulty=difficulty,
        recent_context=recent_context or [],
    )

    return {
        "transcript": transcript,
        **result,
    }


async def conduct_interview_turn(
    *,
    target_role: str,
    topic: str,
    difficulty: str,
    language: str,
    question_number: int,
    question_limit: int,
    conversation: list[dict],
    candidate_answer: str | None = None,
) -> dict:
    if not OLLAMA_API_KEY:
        raise ProviderConfigurationError(
            "Configure OLLAMA_API_KEY in .env."
        )

    system_prompt = """
You are Knoc Interview, a professional human-like job interviewer.
You conduct the interview yourself. You are NOT a hint generator or
an assistant that answers questions for the candidate.

Use the full conversation history to choose the next question.

After each candidate answer:
1. Evaluate correctness, completeness, reasoning, and relevance.
2. Identify important gaps or incorrect claims.
3. Choose exactly one strategy:
   - follow_up: probe the candidate's answer more deeply
   - clarify: ask them to explain a confusing or incorrect claim
   - new_topic: test a different relevant skill
   - increase_difficulty: ask a harder practical question
   - finish: end the interview if the question limit is reached
4. Ask ONE clear question at a time.
5. Do not reveal the ideal answer during the interview.
6. Do not repeat an earlier question unless clarification is necessary.
7. Adapt questions to the selected role, difficulty, and past answers.
8. A weak answer does not mean endlessly repeating the same question.
   Probe once or twice, then test another topic.
9. Never invent candidate experience or claim to have heard audio that
   was not provided.
10. Use the requested interview language.

Return ONLY valid JSON with this structure:
{
  "action": "follow_up | clarify | new_topic | increase_difficulty | finish",
  "question": "the next question, or empty when finishing",
  "evaluation": {
    "score": 0,
    "correctness": "short assessment",
    "completeness": "short assessment",
    "reasoning": "short assessment",
    "feedback": "private feedback for the final report",
    "strengths": ["..."],
    "weaknesses": ["..."]
  },
  "topic": "topic tested by the next question",
  "difficulty": "beginner | intermediate | advanced",
  "final_summary": "short overall summary when finishing, otherwise empty"
}

Score the answer from 0 to 100. If there is no candidate answer
yet, set evaluation.score to 0 and evaluation fields to empty values.
Do not finish before question_limit questions have been asked, unless
the interview cannot continue.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Target role: {target_role}\n"
                f"Interview topic: {topic}\n"
                f"Difficulty: {difficulty}\n"
                f"Language: {language}\n"
                f"Current question number: {question_number}\n"
                f"Maximum questions: {question_limit}\n"
                f"Latest candidate answer: {candidate_answer or '(not answered yet)'}\n"
                "Conversation history (oldest first):\n"
                + json.dumps(conversation[-30:], ensure_ascii=False)
            ),
        },
    ]

    async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
        response = await client.post(
            OLLAMA_CHAT_URL,
            headers={
                "Authorization": f"Bearer {OLLAMA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "format": "json",
                "messages": messages,
                "options": {"temperature": 0.5},
            },
        )
        response.raise_for_status()
        body = response.json()

    content = body.get("message", {}).get("content", "")

    try:
        result = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("Interview AI returned invalid JSON.") from exc

    allowed_actions = {
        "follow_up",
        "clarify",
        "new_topic",
        "increase_difficulty",
        "finish",
    }

    if result.get("action") not in allowed_actions:
        raise RuntimeError("Interview AI returned an invalid action.")

    evaluation = result.get("evaluation")
    if not isinstance(evaluation, dict):
        raise RuntimeError("Interview AI returned no evaluation.")

    try:
        evaluation["score"] = max(
            0, min(100, int(evaluation.get("score", 0)))
        )
    except (TypeError, ValueError):
        evaluation["score"] = 0

    question = result.get("question", "")
    if not isinstance(question, str):
        question = ""

    if result["action"] != "finish" and not question.strip():
        raise RuntimeError("Interview AI did not generate a question.")

    result["question"] = question.strip()
    result["evaluation"] = evaluation
    result["topic"] = str(result.get("topic") or topic)
    result["difficulty"] = str(result.get("difficulty") or difficulty)
    result["final_summary"] = str(result.get("final_summary") or "")

    return result