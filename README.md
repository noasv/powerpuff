# CalibrateAI

CalibrateAI is a runnable competence-calibration and anti-illusion learning platform. It compares a learner's confidence with observable recognition, free recall, explanation, conflict, and transfer evidence. It describes evidence—never personality or psychological diagnoses.

## Problem and solution

A correct selected answer can hide a fragile mental model. CalibrateAI continues beyond right/wrong: **answer → confidence → explanation → recall → conflict → transfer → diagnosis → Socratic tutor → updated profile**. Every submitted attempt is persisted and recomputes mastery, calibration, risks, recommendations, student charts, and teacher analytics.

## Features

- Student registration/login, protected navigation, account deletion API, and role-based teacher access
- Persistent SQLite attempts with confidence, response time, answer changes, explanations, assessments, and explainable gaps
- Explicit adaptive diagnostic sequence with recognition, recall, conflict, transfer, and contextual “Why this task?” messages
- Configurable performance/mastery weights, calibration gap, risk classification, historical smoothing, and multi-signal gap detection
- Structured AI abstraction, evidence-aware no-key mock provider, OpenAI-compatible real provider, validated JSON with repair, timeout/error fallback, and external prompt templates
- Adaptive multi-turn Socratic tutor with changed-condition verification, responsive concept dependency map, Recharts dashboards, and teacher concept/student analytics
- Loading, error, empty, validation, retry, mobile navigation, and accessible form states
- 3 subjects, 30 concepts, 120 questions, demo history, and test coverage for engines, auth, authorization, dashboard, and mock AI

## Architecture

```text
React + TypeScript + Vite + Recharts
                 │ REST/JWT
FastAPI ─ auth / assessment / analytics / AI facade
                 │
SQLAlchemy ─ SQLite (development) / PostgreSQL-compatible ORM
                 │
AIProvider ─ RealAIProvider ─fallback→ MockAIProvider
```

Business rules live in `backend/app/services` and `backend/app/analytics`; HTTP orchestration is isolated in `backend/app/api`; provider implementations are in `backend/app/ai`. The frontend uses typed domain interfaces and a single authenticated API client.

## Quick start with Docker

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs.

## Local installation

Requires Python 3.11+ and Node 20+.

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` to port 8000. Set `VITE_API_URL` only when the API is hosted elsewhere.

## Environment variables

Copy `.env.example`. Important variables:

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./calibrate.db` |
| `JWT_SECRET` | JWT signing secret (replace in production) | development-only value |
| `AI_API_KEY` | Server-only compatible API key | empty / Demo Mode |
| `AI_BASE_URL` | OpenAI-compatible API root | `https://api.openai.com/v1` |
| `AI_MODEL` | Chat model | `gpt-4o-mini` |
| `CORS_ORIGINS` | Comma-separated web origins | `http://localhost:5173` |

Never prefix the AI key with `VITE_`; it must never reach the browser.

## Seed and demo flow

Run `python backend/seed.py` from the repository root or `python seed.py` inside `backend`. It is idempotent and creates:

- **Student:** `student@demo.com` / `Demo123!`
- **Teacher:** `teacher@demo.com` / `Demo123!`
- Mathematics, Physics, Chemistry; 10 concepts and four task types per subject; existing fragile learning history.

Sign in as the student, choose Physics → Newton's Laws, and complete standard, recall, conflict, and transfer tasks. Each submission updates the database. Open the Tutor for guided intervention, then sign in as the teacher to inspect recalculated class evidence.

## Demo Mode and AI configuration

With no `AI_API_KEY`, the entire flow uses `MockAIProvider` and the Tutor shows Demo mode. With a key, `RealAIProvider` requests schema-validated JSON from an OpenAI-compatible endpoint; malformed output receives one repair attempt. Network errors, timeouts, invalid payloads, or provider failures fall back to the evidence-aware mock provider, so diagnostics remain available. Keys stay on the backend.

For the hosted OpenAI API, add these server-side lines to the repository-root `.env` (substitute your own secret):

```dotenv
AI_API_KEY=<YOUR_OPENAI_API_KEY>
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

Restart with `docker compose down && docker compose up --build -d`. Sign in as a student, open **AI Tutor**, send a reasoning response, and confirm the status beside the concept changes to **Real AI connected**. A **Demo mode** status means no key is configured or the configured provider was unavailable for that response. Do not put the key in `frontend/`, browser storage, `VITE_API_URL`, or any variable beginning with `VITE_`.

Prompt files under `backend/app/prompts/` define role, input, task, safety rules, JSON output, and examples. AI language is restricted to observable learning evidence.

## Scoring

Configured in `backend/app/config/scoring.py`:

```text
performance = .35 accuracy + .25 recall + .25 transfer + .15 explanation
calibration_gap = confidence / 5 - performance
mastery = .30 accuracy + .20 recall + .20 transfer
        + .15 explanation + .15 calibration_quality
```

Mastery is historically smoothed after the first assessment. `MASTERED`, `STABLE`, `FRAGILE`, and `AT RISK` require multiple signals. Gaps store their exact evidence and a recommended action; response time is retained only as supporting evidence and never interpreted alone.

## API overview

FastAPI provides interactive, schema-derived documentation at `/docs`. Major routes:

- `/api/auth/register`, `/login`, `/me` (GET current user, DELETE account)
- `/api/subjects`, `/api/subjects/{id}/concepts`, `/api/questions/next`
- `/api/attempts`, `/api/attempts/{id}/explain`
- `/api/assessments/{concept_id}/recall|conflict`
- `/api/student/dashboard|concepts|gaps`
- `/api/teacher/dashboard|students|concepts`, `/api/teacher/students/{id}`
- `/api/ai/generate-question|analyze-explanation|generate-conflict|tutor`

All learning and analytics endpoints require Bearer JWT authentication; teacher routes enforce role authorization.

## Testing and quality checks

```bash
cd backend && pytest -q
cd frontend && npm run build
```

For a clean seed validation, remove only your local development database and run `python seed.py` again. Do not do this against retained user data.

## Project structure

```text
backend/app/{api,ai,analytics,config,prompts,services}
backend/tests
frontend/src/{components,pages,services,types}
.env.example
docker-compose.yml
```

## Privacy and security

Passwords use Argon2 hashing and authentication uses expiring JWTs. Inputs are validated by Pydantic and the ORM uses parameterized SQL. The platform stores only necessary educational data; it does not access camera, microphone, browser history, other apps, or private messages. Change the JWT secret, configure restrictive CORS, and deploy behind HTTPS in production.
