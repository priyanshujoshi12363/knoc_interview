
"""
Knoc Interview - Integration Test

Tests:
1. FastAPI/OpenAPI availability
2. Authentication
3. Cloudflare STT using the existing test.wav
4. Interview creation, start, and completion
5. Whether question/answer/scoring routes are exposed

Candidate answers are typed; no microphone is required.

Run from the backend directory:
    python tests/test_full_interview_flow.py
"""

import os
import sys
import json
import wave
import asyncio
from pathlib import Path

import requests
from dotenv import load_dotenv

# Make backend imports work when this file is run from tests/.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

API_PREFIX = "/api/v1"
EMAIL = os.getenv("TEST_EMAIL", "")
PASSWORD = os.getenv("TEST_PASSWORD", "")
AUDIO_FILE = ROOT / "test.wav"

passed = 0
failed = 0
not_implemented = 0
token = None


def report(name, status, details=""):
    global passed, failed, not_implemented

    print(f"  {status:17} {name}")
    if details:
        print(f"                    {details}")

    if status == "PASS":
        passed += 1
    elif status == "FAIL":
        failed += 1
    elif status == "NOT IMPLEMENTED":
        not_implemented += 1


def api_request(method, path, **kwargs):
    url = f"{BASE_URL}{API_PREFIX}{path}"
    return requests.request(
        method,
        url,
        timeout=45,
        **kwargs,
    )


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {"raw_response": response.text[:1000]}


def get_pcm_16k_mono(audio_path):
    """
    Convert a WAV file to raw PCM16, 16 kHz, mono.
    audioop is available in Python 3.12, but was removed
    in Python 3.13. This script targets your Python 3.12 venv.
    """
    import audioop

    with wave.open(str(audio_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())

    if not pcm:
        raise ValueError("WAV contains no audio frames.")

    if sample_width != 2:
        pcm = audioop.lin2lin(pcm, sample_width, 2)
        sample_width = 2

    if channels == 2:
        pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
    elif channels != 1:
        raise ValueError(
            f"Unsupported audio channel count: {channels}"
        )

    if sample_rate != 16000:
        pcm, _ = audioop.ratecv(
            pcm, 2, 1, sample_rate, 16000, None
        )

    print(
        f"  Audio: {sample_rate} Hz, {channels} channel(s), "
        f"{len(pcm)} PCM bytes after conversion"
    )
    return pcm


async def run_cloudflare_stt():
    """
    Calls the actual project service, which uses Cloudflare
    credentials from .env. Does not mock the provider.
    """
    from services.live_copilot import transcribe_pcm

    pcm = get_pcm_16k_mono(AUDIO_FILE)
    transcript = await transcribe_pcm(pcm, language="en")

    if not isinstance(transcript, str) or not transcript.strip():
        raise RuntimeError(
            "Cloudflare STT returned an empty transcript."
        )

    return transcript.strip()


def test_server():
    try:
        response = requests.get(
            f"{BASE_URL}/openapi.json",
            timeout=30,
        )
    except requests.RequestException as exc:
        report("FastAPI server", "FAIL", str(exc))
        return None

    report(
        "FastAPI/OpenAPI",
        "PASS" if response.status_code == 200 else "FAIL",
        f"HTTP {response.status_code}",
    )

    if response.status_code != 200:
        print(response.text[:1000])
        return None

    return safe_json(response)


def test_login():
    global token

    if not EMAIL or not PASSWORD:
        report(
            "Login",
            "FAIL",
            "Set TEST_EMAIL and TEST_PASSWORD in PowerShell.",
        )
        return False

    try:
        response = api_request(
            "POST",
            "/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
        )
    except requests.RequestException as exc:
        report("Login", "FAIL", str(exc))
        return False

    data = safe_json(response)

    token = data.get("access_token")
    if not token and isinstance(data.get("tokens"), dict):
        token = data["tokens"].get("access_token")

    ok = response.status_code == 200 and bool(token)
    report(
        "Authentication",
        "PASS" if ok else "FAIL",
        f"HTTP {response.status_code}",
    )

    if not ok:
        print(json.dumps(data, indent=2)[:1500])

    return ok


def inspect_flow_routes(openapi):
    """
    OpenAPI does not normally list WebSocket routes.
    This discovers HTTP routes related to question/answer/scoring.
    """
    paths = openapi.get("paths", {})
    keywords = (
        "question", "answer", "score", "evaluation",
        "result", "summary", "hint",
    )

    found = []
    for path, methods in paths.items():
        if any(word in path.lower() for word in keywords):
            verbs = [
                method.upper()
                for method in methods
                if method.lower() in {
                    "get", "post", "put", "patch", "delete"
                }
            ]
            found.append(f"{', '.join(verbs)} {path}")

    print("\n  Discovered HTTP flow routes:")
    if found:
        for route in found:
            print(f"    {route}")
    else:
        print("    No question/answer/scoring routes found in OpenAPI.")

    score_routes = [
        route for route in found
        if any(word in route.lower()
               for word in ("score", "evaluation", "result"))
    ]

    if score_routes:
        report("HTTP scoring route discovery", "PASS",
               "Potential scoring routes found; contract still needs testing.")
    else:
        report(
            "HTTP scoring route discovery",
            "NOT IMPLEMENTED",
            "No matching scoring route in OpenAPI. "
            "Scoring cannot be verified through HTTP yet.",
        )


def test_interview_lifecycle():
    headers = {"Authorization": f"Bearer {token}"}

    print("\n[INTERVIEW] Create session")

    payload = {
        "mode": "practice",
        "topic": "Python and Backend Development",
        "target_role": "Backend Developer",
        "difficulty": "intermediate",
        "question_count": 3,
        "duration_minutes": 5,
        "hint_mode": "both",
        "language": "en",
    }

    response = api_request(
        "POST", "/interviews",
        headers=headers, json=payload,
    )

    data = safe_json(response)
    if response.status_code not in (200, 201):
        report("Create interview", "FAIL",
               f"HTTP {response.status_code}: {data}")
        return

    interview_id = data.get("id")
    if not interview_id:
        report("Create interview ID", "FAIL",
               json.dumps(data)[:500])
        return

    report("Create interview", "PASS", f"ID: {interview_id}")
    report(
        "Initial status",
        "PASS" if data.get("status") == "created" else "FAIL",
        f"Status: {data.get('status')}",
    )

    print("\n[INTERVIEW] Start session")

    response = api_request(
        "POST", f"/interviews/{interview_id}/start",
        headers=headers,
    )
    data = safe_json(response)

    started = (
        response.status_code == 200
        and data.get("status") == "in_progress"
    )
    report(
        "Start interview",
        "PASS" if started else "FAIL",
        f"HTTP {response.status_code}: {data}",
    )

    if not started:
        return

    print("\n[INTERVIEW] Typed candidate-answer fixture")

    # These are test inputs only. They are NOT submitted as answers
    # unless the backend implements an answer-submission endpoint.
    typed_answers = [
        {
            "question": "What is a Python dictionary?",
            "answer": (
                "A dictionary stores key-value pairs. "
                "Keys are unique and values are accessed by key."
            ),
        },
        {
            "question": "What is the difference between a list and a tuple?",
            "answer": (
                "A list is mutable, while a tuple is immutable. "
                "Both can store multiple items."
            ),
        },
        {
            "question": "What is an HTTP 401 response?",
            "answer": (
                "HTTP 401 means authentication is required "
                "or the supplied credentials are invalid."
            ),
        },
    ]

    for index, item in enumerate(typed_answers, start=1):
        print(f"\n  Candidate answer {index}:")
        print(f"    Question: {item['question']}")
        print(f"    Answer:   {item['answer']}")

    # Discover actual answer endpoints before claiming these answers
    # were evaluated or saved.
    try:
        openapi_response = requests.get(
            f"{BASE_URL}/openapi.json", timeout=30
        )
        paths = safe_json(openapi_response).get("paths", {})
    except requests.RequestException:
        paths = {}

    answer_paths = [
        path for path in paths
        if any(term in path.lower()
               for term in ("answer", "submit"))
    ]

    if answer_paths:
        report(
            "Answer endpoint discovery",
            "PASS",
            "Found: " + ", ".join(answer_paths),
        )
        report(
            "Answer submission and scoring",
            "NOT IMPLEMENTED",
            "Endpoint payload and scoring contract must be inspected "
            "before sending guessed requests.",
        )
    else:
        report(
            "Answer submission and scoring",
            "NOT IMPLEMENTED",
            "Typed answers are fixtures only; no answer/submit route "
            "was found in OpenAPI.",
        )

    print("\n[INTERVIEW] Complete session")

    response = api_request(
        "POST",
        f"/interviews/{interview_id}/end",
        headers=headers,
        json={"reason": "Integration test completed"},
    )
    data = safe_json(response)

    ok = response.status_code == 200
    report(
        "End interview",
        "PASS" if ok else "FAIL",
        f"HTTP {response.status_code}",
    )

    if ok:
        final_interview = data.get("interview", {})
        report(
            "Completed status",
            "PASS" if final_interview.get("status") == "completed"
            else "FAIL",
            f"Status: {final_interview.get('status')}",
        )
        print(f"  Turn count reported: {data.get('turn_count', 'N/A')}")
        print(
            "  Score reported: "
            f"{final_interview.get('score', 'Not returned')}"
        )


def main():
    print("=" * 68)
    print("       KNOC INTERVIEW - FULL INTEGRATION DIAGNOSTICS")
    print("=" * 68)
    print(f"API: {BASE_URL}")

    openapi = test_server()
    if openapi is None:
        return 2

    print("\n[1] REAL CLOUDFLARE SPEECH-TO-TEXT")
    if not AUDIO_FILE.exists():
        report(
            "Cloudflare STT",
            "FAIL",
            f"Audio fixture missing: {AUDIO_FILE}",
        )
    else:
        try:
            transcript = asyncio.run(run_cloudflare_stt())
            report("Cloudflare STT", "PASS",
                   "Actual transcription received.")
            print("\n  Transcribed text:")
            print(f"    {transcript}")
        except Exception as exc:
            report("Cloudflare STT", "FAIL",
                   f"{type(exc).__name__}: {exc}")

    print("\n[2] AUTHENTICATION")
    if test_login():
        print("\n[3] INTERVIEW LIFECYCLE")
        try:
            test_interview_lifecycle()
        except requests.RequestException as exc:
            report("Interview lifecycle", "FAIL", str(exc))
        except Exception as exc:
            report(
                "Interview lifecycle",
                "FAIL",
                f"{type(exc).__name__}: {exc}",
            )

    print("\n[4] FLOW ROUTE DISCOVERY")
    inspect_flow_routes(openapi)

    print("\n" + "=" * 68)
    print(f"PASS: {passed} | FAIL: {failed} | "
          f"NOT IMPLEMENTED / UNVERIFIED: {not_implemented}")
    print("=" * 68)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
