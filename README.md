
# Knoc Interview — Backend

FastAPI backend for Knoc Interview, an AI-powered interview preparation
Android application. It uses MongoDB Atlas for persistence and is designed
to support practice interviews, live voice interviews, adaptive follow-up
questions, hints, and performance summaries.

## Tech Stack

- Python
- FastAPI
- MongoDB Atlas
- PyMongo AsyncMongoClient
- Pydantic
- python-dotenv
- Uvicorn

## Project Structure

```text
BACKEND/
├── main.py
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── db/
│   ├── __init__.py
│   └── index.py
└── models/
    ├── __init__.py
    ├── common.py
    ├── auth.py
    ├── user.py
    ├── interview.py
    └── evaluation.py
```

## Prerequisites

- Python 3.10 or newer
- MongoDB Atlas account
- MongoDB Atlas database user and connection string

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd BACKEND
```

If you already have the project locally, open a terminal in the
`BACKEND` directory instead.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install fastapi "uvicorn[standard]" pymongo python-dotenv "pydantic[email]"
```

Save the installed dependencies:

```bash
python -m pip freeze > requirements.txt
```

## Environment Configuration

Create a `.env` file in the project root:

```env
MONGODB_URL="mongodb+srv://<username>:<password>@cluster0.vugudi3.mongodb.net/knoc_interview?appName=Cluster0"
```

Replace `<username>` and `<password>` with your MongoDB Atlas credentials.

Ensure your Atlas network access rules allow your development machine
to connect. Never commit `.env` or publish database credentials.

## Run the Server

From the project root:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will attempt to connect to MongoDB during startup.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API welcome message |
| GET | `/api/v1/health` | API health check |
| GET | `/api/v1/health/database` | MongoDB connection check |
| GET | `/docs` | Interactive Swagger API documentation |

Open the documentation in your browser:

http://127.0.0.1:8000/docs

## Android Development

When connecting the Android app to the backend:

- Android emulator: `http://10.0.2.2:8000`
- Physical Android device on the same Wi-Fi: `http://<YOUR_PC_LAN_IP>:8000`
- Deployed backend: use its public HTTPS URL.

The local URLs are for development only. Production deployments should
use HTTPS and secure server-side configuration.

## MongoDB Collections

The planned collections are:

- `users` — user profiles and authentication records
- `interviews` — interview configuration and lifecycle
- `interview_turns` — questions, answers, transcripts, and hints
- `evaluations` — scores, feedback, and interview summaries

MongoDB collections are generally created when documents are first inserted.
Defining a collection variable alone does not create it.

## Planned Features

- User registration and login
- Profile and dashboard
- Practice mode with topic selection
- Live voice interview mode
- Context-aware follow-up questions
- Optional interview hints
- Interview history and summaries
- Performance tracking and practice streaks

## Security

- Keep database credentials in environment variables.
- Hash passwords before storing them.
- Protect user-owned resources with authentication and ownership checks.
- Keep AI provider API keys on the backend.
- Validate incoming requests and limit request sizes.
- Use HTTPS in production.

## Development Status

The backend foundation and initial Pydantic schemas are being developed.
Authentication, interview lifecycle APIs, AI voice integration, and
evaluation services will be implemented incrementally.

## License

To be decided.
