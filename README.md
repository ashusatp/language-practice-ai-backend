# Khoo AI - Voice Language Practice Backend

An advanced, real-time voice AI backend designed for conversational language practice and fluency coaching. The system pairs learners with interactive AI conversation partners in real-time WebRTC audio rooms, dynamically adapts to user proficiency levels, and delivers comprehensive linguistic feedback and scoring upon session completion.

---

## 🌟 What This Project Is For

**Khoo AI** is built to solve the anxiety and accessibility barriers of learning a new language. Rather than passive multiple-choice drills, Khoo AI enables users to engage in natural, zero-latency, spoken voice conversations with an intelligent AI tutor.

### Key Capabilities:
- **Zero-Latency Voice Conversations:** Low-latency, full-duplex WebRTC voice rooms where users and the AI can speak and listen naturally.
- **Adaptive Pedagogy:** The AI dynamically adjusts its vocabulary, pacing, sentence complexity, and corrective feedback according to the learner's declared skill level (*Beginner*, *Intermediate*, or *Advanced*).
- **Multi-Language & Indian Accents:** Full conversational support for English and Hindi with culturally native Indian accents and natural pronunciation.
- **Detailed Post-Session AI Feedback:** Automatically extracts dialogue transcripts and generates detailed linguistic evaluations, fluency scores, grammar error corrections with explanations, and key vocabulary.
- **Quota & Subscription Management:** Tiered usage control featuring a 10-minute lifetime free trial, Pro (60 mins/day), and Pro Max (100 mins/day) with automatic midnight (IST) daily quota resets.
- **Secure Email Verification & Auth:** JWT-based authentication with cryptographically secure token-based email verification and automated transactional welcome emails.

---

## 🏗️ Architecture Overview

The system is decoupled into two primary backend services sharing a centralized PostgreSQL database:

```mermaid
graph TD
    Client[Web / Mobile Frontend]
    
    subgraph "FastAPI Web Server (Render)"
        API[FastAPI REST API]
        Auth[JWT & Email Verification]
        Subs[Subscription & Quota Engine]
        Tokens[LiveKit Token Dispatcher]
        Hist[Session History & Feedback API]
    end

    subgraph "LiveKit Cloud (WebRTC)"
        LKCloud[LiveKit Audio Room]
    end

    subgraph "Voice Agent Worker (Railway)"
        Worker[LiveKit Agent Server]
        STT[Deepgram Nova-3 STT]
        LLM[Gemma-4-31B LLM]
        TTS[Sarvam Bulbul:v3 TTS]
        VAD[Turn Detector & Noise Canceller]
    end

    subgraph "Persistence & Processing"
        PG[(PostgreSQL Database)]
        Queue[SKIP LOCKED Job Queue]
        Evaluator[OpenAI GPT-4o-mini Evaluator]
    end

    Client -->|REST Requests| API
    API -->|Generate Room Token| Tokens
    Tokens --> Client
    Client <-->|WebRTC Voice Stream| LKCloud
    LKCloud <-->|RTC Dispatch| Worker
    Worker --> STT
    Worker --> LLM
    Worker --> TTS
    Worker --> VAD
    Worker -->|Log Transcript & Usage| PG
    Worker -->|Direct Persist or Enqueue| Evaluator
    Evaluator -->|Save Feedback & Scores| PG
    API --> PG
```

1. **FastAPI Web Service:** Handles user authentication, token issuance, subscription quota tracking, content catalogs (languages, voices, topics), and session feedback APIs.
2. **LiveKit Agent Worker:** A dedicated Python worker process connecting to LiveKit Cloud. It listens for room connections, streams audio bi-directionally, orchestrates the STT-LLM-TTS pipeline, and logs conversation turns.
3. **Evaluation Engine:** Generates comprehensive linguistic assessments (via direct execution or PostgreSQL-backed `SKIP LOCKED` worker fallback).

---

## 🤖 AI Models & Providers

| Component | Provider | Model | Description / Purpose |
| :--- | :--- | :--- | :--- |
| **Speech-to-Text (STT)** | **Deepgram** | `nova-3` | Ultra-fast, high-accuracy real-time speech transcription supporting English (`en`) and Hindi (`hi`). |
| **Language Model (LLM)** | **Google / LiveKit Inference** | `google/gemma-4-31b-it` | Conversation partner running via LiveKit Inference; provides empathetic, prompt-guided tutoring tailored to Beginner, Intermediate, and Advanced learners. |
| **Text-to-Speech (TTS)** | **Sarvam AI** | `bulbul:v3` | High-fidelity Indian-accent voice synthesis in Indian English (`en-IN`) and Hindi (`hi-IN`) with 30+ native voices (e.g., *Shubh*, *Amelia*, *Aditya*, *Priya*, *Kabir*). |
| **Turn Detection (VAD)** | **LiveKit Agents** | `inference.TurnDetector()` | Detects end-of-speech and user interruptions to enable natural conversational turns without push-to-talk. |
| **Audio Enhancement** | **ai-coustics** | `QUAIL_VF_S` | Neural noise cancellation and speech enhancement applied to inbound learner microphone audio. |
| **Session Analysis & Feedback** | **OpenAI** | `gpt-4o-mini` | Analyzes transcripts to generate fluency scores (1.0–5.0), grammatical mistake corrections with explanations, sentiment, key points, and vocabulary. |

---

## 💻 Technology Stack

### Core & Frameworks
- **Language:** Python 3.12+
- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) with asynchronous route handlers and Pydantic v2 schemas.
- **ASGI Server:** [Uvicorn](https://www.uvicorn.org/)
- **Package Manager:** [Astral uv](https://github.com/astral-sh/uv) for fast, deterministic dependency resolution via `pyproject.toml` and `uv.lock`.

### Real-Time & Agents
- **LiveKit Agents SDK:** `livekit-agents~=1.8`
- **LiveKit Plugins:** `livekit-plugins-deepgram`, `livekit-plugins-sarvam`, `livekit-plugins-ai-coustics`
- **WebRTC Transport:** LiveKit Cloud

### Database & Storage
- **Database:** PostgreSQL (15+)
- **ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async engine with `asyncpg` and `psycopg3 binary`)
- **Schema Migrations:** [Alembic](https://alembic.sqlalchemy.org/)

### Security & Utilities
- **Authentication:** JWT tokens (`HS256`) via `python-jose` / `pyjwt`
- **Password Hashing:** `bcrypt`
- **Transactional Mailer:** `fastapi-mail` (SMTP over SSL/TLS port 465)
- **Configuration:** `pydantic-settings` & `python-dotenv`

---

## 📁 Repository Structure

```
├── alembic/                  # Database migration scripts
│   └── versions/             # Version migrations (schema, tables, indices)
├── agent/                    # LiveKit Voice Agent Worker
│   ├── agent.py              # Assistant prompt logic and persona definitions
│   ├── providers.py          # STT (Deepgram) and TTS (Sarvam) configuration
│   └── rtc_entrypoint.py     # LiveKit WebRTC room entrypoint & lifecycle handlers
├── app/                      # FastAPI Application
│   ├── apis/                 # API route endpoints
│   │   ├── auth.py           # Registration, login, email verification
│   │   ├── content.py        # Languages, voices, topics, scenarios
│   │   ├── livekit.py        # LiveKit token dispatching
│   │   ├── session.py        # Session history, polling, feedback, ratings
│   │   └── subscription.py   # Quota usage and plan status
│   ├── db/                   # Async database engine & session fixtures
│   ├── dependencies/         # FastAPI Dependency Injection (Auth, Repos, Services)
│   ├── models/               # SQLAlchemy ORM models (User, Session, Feedback, Job, etc.)
│   ├── repositories/         # Data access layer (User, Session, Subscription)
│   ├── services/             # Business logic (SessionProcessor, AuthService, etc.)
│   ├── types/                # Pydantic request/response schemas
│   ├── utils/                # Security helpers (JWT, bcrypt, SMTP mailer)
│   ├── job_worker.py         # PostgreSQL SKIP LOCKED transactional job worker
│   └── main.py               # FastAPI application factory & lifespan
├── config/                   # Centralized Pydantic application configuration
├── server.py                 # Standalone LiveKit Agent runner (`start` / `dev`)
├── main.py                   # Root entrypoint with auto-environment detection
├── Dockerfile                # Production containerfile optimized for agent deployment
├── railway.json              # Railway service configuration
├── render.yaml               # Render Infrastructure-as-Code deployment blueprint
├── pyproject.toml            # Project dependency specifications
└── uv.lock                   # Deterministic lockfile
```

---

## ⚙️ Environment Variables

Create a `.env` or `.env.local` file in the project root:

```ini
# --- Environment & App ---
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
API_HOST=0.0.0.0
PORT=8000
CLIENT_ENDPOINT=http://localhost:5173

# --- Database (PostgreSQL) ---
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/call_engine

# --- JWT Authentication ---
JWT_SECRET_KEY=generate-a-strong-random-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# --- LiveKit Cloud Credentials ---
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
AGENT_NAME=call-engine

# --- AI Provider API Keys ---
DEEPGRAM_API_KEY=your_deepgram_api_key
SARVAM_API_KEY=your_sarvam_api_key
OPENAI_API_KEY=your_openai_api_key

# --- SMTP / Email Settings ---
MAIL_USERNAME=noreply@yourdomain.com
MAIL_PASSWORD=your_email_password
MAIL_FROM=noreply@yourdomain.com
MAIL_SERVER=smtp.yourhost.com
MAIL_PORT=465
MAIL_SSL_TLS=true
MAIL_STARTTLS=false
USE_CREDENTIALS=true
VALIDATE_CERTS=true
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) installed:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Or on macOS via Homebrew:
  brew install uv
  ```
- PostgreSQL running locally or accessible via remote connection.

### 2. Install Dependencies
```bash
# Clone the repository
git clone https://github.com/ashusatp/language-practice-ai-backend.git
cd language-practice-ai-backend

# Install all frozen dependencies into virtualenv
uv sync --frozen
```

### 3. Run Database Migrations
```bash
uv run alembic upgrade head
```

### 4. Start the FastAPI Web Server
```bash
# Starts FastAPI with auto-reload on http://localhost:8000
uv run python main.py
```
Interactive OpenAPI documentation will be accessible at `http://localhost:8000/docs`.

### 5. Start the LiveKit Agent Worker (Local Dev Mode)
In a separate terminal window:
```bash
# Starts LiveKit agent in development mode
uv run python server.py dev
```

---

## ☁️ Deployment Guide

The architecture supports deploying the **FastAPI Web API** on Render and the **LiveKit Voice Agent** on Railway.

### Deploying the Voice Agent on Railway
The voice agent requires persistent WebSocket connectivity to LiveKit Cloud.

1. Create a new service on [Railway](https://railway.com/) linked to this repository.
2. Under **Settings** -> **Build**, set Builder to **Dockerfile**.
3. Under **Settings** -> **Deploy**, ensure the Start Command is:
   ```bash
   uv run python server.py start
   ```
4. Set the following environment variables in the Railway dashboard:
   - `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
   - `DEEPGRAM_API_KEY`, `SARVAM_API_KEY`, `OPENAI_API_KEY`
   - `DATABASE_URL`

### Deploying the FastAPI Web API on Render
1. Create a Web Service on [Render](https://render.com/) or connect the included [render.yaml](file:///Users/ashutosh/Documents/All%20in%20One/khoo%20ai/backend/render.yaml).
2. Set Build Command:
   ```bash
   pip install uv && uv sync --frozen && uv run alembic upgrade head
   ```
3. Set Start Command:
   ```bash
   uv run python main.py
   ```
4. Configure all environment variables (`DATABASE_URL`, `JWT_SECRET_KEY`, `MAIL_*`, LiveKit keys).

---

## 📡 API Reference Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user account and dispatch verification email |
| `POST` | `/auth/login` | Authenticate user and return JWT bearer token |
| `GET` | `/auth/verify-email?token=...` | Verify user email address with single-use token |
| `POST` | `/auth/resend-verification` | Resend email verification link |
| `POST` | `/livekit/token` | Generate LiveKit participant token with embedded room metadata |
| `GET` | `/session` | Retrieve paginated user session history with ratings and metrics |
| `GET` | `/session/{session_id}` | Retrieve full session summary, mistakes, scores, and transcript |
| `GET` | `/session/status/{room_id}` | Poll background processing status of a completed room |
| `POST` | `/session/{session_id}/rating`| Submit a 1–5 star rating and written review for a session |
| `GET` | `/subscription/status` | Get user quota (tier, lifetime minutes, daily minutes remaining) |
| `GET` | `/content/languages` | List supported practice languages |
| `GET` | `/content/voices` | List available native Indian voices |
| `GET` | `/content/topics` | List available conversational themes and scenarios |

---

## 🛡️ License

This project is proprietary and confidential. Developed for Khoo AI Language Practice.
