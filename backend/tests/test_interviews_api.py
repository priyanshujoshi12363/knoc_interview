
import os
import sys
import json
import requests

BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

API_PREFIX = "/api/v1"

EMAIL = os.getenv("TEST_EMAIL", "")
PASSWORD = os.getenv("TEST_PASSWORD", "")

passed = 0
failed = 0


def check(name, condition, details=""):
    global passed, failed

    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        if details:
            print(f"        {details}")


def api_request(method, path, **kwargs):
    url = f"{BASE_URL}{API_PREFIX}{path}"

    try:
        return requests.request(
            method,
            url,
            timeout=30,
            **kwargs,
        )
    except requests.RequestException as exc:
        print(f"\nRequest failed: {url}")
        print(f"Reason: {exc}")
        sys.exit(2)


def print_response(response):
    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)


def main():
    global passed, failed

    print("=" * 60)
    print("       KNOC INTERVIEW - REAL API INTEGRATION TEST")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")

    # 1. Server
    print("\n[1] SERVER")

    try:
        response = requests.get(
            f"{BASE_URL}/openapi.json",
            timeout=30,
        )
        check(
            "FastAPI server reachable",
            response.status_code == 200,
            f"HTTP {response.status_code}",
        )
    except requests.RequestException as exc:
        check("FastAPI server reachable", False, str(exc))
        print("\nStart the backend in another terminal:")
        print("python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
        sys.exit(2)

    if response.status_code != 200:
        print("Server did not return OpenAPI schema.")
        print_response(response)
        sys.exit(2)

    # 2. Login
    print("\n[2] AUTHENTICATION")

    if not EMAIL or not PASSWORD:
        print("Set TEST_EMAIL and TEST_PASSWORD in PowerShell first.")
        sys.exit(2)

    response = api_request(
        "POST",
        "/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
    )

    check(
        "Login successful",
        response.status_code == 200,
        f"HTTP {response.status_code}: {response.text[:300]}",
    )

    if response.status_code != 200:
        print_response(response)
        sys.exit(2)

    login_data = response.json()
    token = login_data.get("access_token")

    if not token and isinstance(login_data.get("tokens"), dict):
        token = login_data["tokens"].get("access_token")

    if not token:
        print("Login response did not contain access_token.")
        print_response(response)
        sys.exit(2)

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Unauthorized access
    print("\n[3] AUTHORIZATION")

    response = api_request("GET", "/interviews")
    check(
        "Reject requests without token",
        response.status_code in (401, 403),
        f"HTTP {response.status_code}",
    )

    # 4. Create interview
    print("\n[4] CREATE INTERVIEW")

    payload = {
        "mode": "practice",
        "topic": "Python API Testing",
        "target_role": "Backend Developer",
        "difficulty": "intermediate",
        "question_count": 5,
        "duration_minutes": 10,
        "hint_mode": "both",
        "language": "en",
    }

    response = api_request(
        "POST",
        "/interviews",
        headers=headers,
        json=payload,
    )

    check(
        "Create interview",
        response.status_code in (200, 201),
        f"HTTP {response.status_code}: {response.text[:300]}",
    )

    if response.status_code not in (200, 201):
        print_response(response)
        sys.exit(1)

    created = response.json()
    interview_id = created.get("id")

    check("Response contains ID", bool(interview_id))
    check(
        "Initial status is created",
        created.get("status") == "created",
        f"Actual status: {created.get('status')}",
    )

    if not interview_id:
        print_response(response)
        sys.exit(1)

    print(f"Interview ID: {interview_id}")

    # 5. List interviews
    print("\n[5] LIST INTERVIEWS")

    response = api_request(
        "GET",
        "/interviews?page=1&page_size=20",
        headers=headers,
    )

    check(
        "List interviews",
        response.status_code == 200,
        f"HTTP {response.status_code}",
    )

    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])

        check("Response contains items array", isinstance(items, list))
        check(
            "Created interview appears in list",
            any(item.get("id") == interview_id for item in items),
        )

    # 6. Interview details
    print("\n[6] INTERVIEW DETAILS")

    response = api_request(
        "GET",
        f"/interviews/{interview_id}",
        headers=headers,
    )

    check(
        "Get interview details",
        response.status_code == 200,
        f"HTTP {response.status_code}: {response.text[:300]}",
    )

    if response.status_code == 200:
        data = response.json()
        check("Correct interview ID", data.get("id") == interview_id)
        check("Turns array exists", isinstance(data.get("turns"), list))

    # 7. Validation
    print("\n[7] VALIDATION")

    response = api_request(
        "POST",
        "/interviews",
        headers=headers,
        json={"mode": "invalid", "topic": "x"},
    )

    check(
        "Invalid payload rejected",
        response.status_code == 422,
        f"HTTP {response.status_code}",
    )

    response = api_request(
        "GET",
        "/interviews/not-a-valid-object-id",
        headers=headers,
    )

    check(
        "Invalid interview ID rejected",
        response.status_code == 404,
        f"HTTP {response.status_code}",
    )

    # 8. Start
    print("\n[8] START INTERVIEW")

    response = api_request(
        "POST",
        f"/interviews/{interview_id}/start",
        headers=headers,
    )

    check(
        "Start interview",
        response.status_code == 200,
        f"HTTP {response.status_code}: {response.text[:300]}",
    )

    if response.status_code == 200:
        check(
            "Status becomes in_progress",
            response.json().get("status") == "in_progress",
        )

        response = api_request(
            "POST",
            f"/interviews/{interview_id}/start",
            headers=headers,
        )

        check(
            "Starting twice is rejected",
            response.status_code == 409,
            f"HTTP {response.status_code}",
        )

        # 9. End
        print("\n[9] END INTERVIEW")

        response = api_request(
            "POST",
            f"/interviews/{interview_id}/end",
            headers=headers,
            json={"reason": "API integration test"},
        )

        check(
            "End interview",
            response.status_code == 200,
            f"HTTP {response.status_code}: {response.text[:300]}",
        )

        if response.status_code == 200:
            result = response.json()
            interview = result.get("interview", {})

            check(
                "Final status is completed",
                interview.get("status") == "completed",
            )
            check(
                "Turn count returned",
                isinstance(result.get("turn_count"), int),
            )

    # 10. Final state
    print("\n[10] FINAL STATE")

    response = api_request(
        "GET",
        f"/interviews/{interview_id}",
        headers=headers,
    )

    check(
        "Fetch final interview",
        response.status_code == 200,
        f"HTTP {response.status_code}",
    )

    if response.status_code == 200:
        final_data = response.json()
        print(f"  ID:     {final_data.get('id')}")
        print(f"  Topic:  {final_data.get('topic')}")
        print(f"  Status: {final_data.get('status')}")
        print(f"  Turns:  {len(final_data.get('turns', []))}")

    print("\n" + "=" * 60)
    print(f"RESULT: {passed} passed | {failed} failed")
    print("=" * 60)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
    