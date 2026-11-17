# Yes Officer — Quiz & Live Polling

Real-time MCQ polls with ephemeral class chat and AI chat insights for remote classes.
Design and decisions: `docs/ARCHITECTURE_PROPOSAL.md`. Product context: `PRODUCT.md`.

| Part | Stack |
|---|---|
| `backend/` | FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · Redis (live state + Celery broker) · Celery · Claude API for chat analysis |
| `frontend/` | React 18 + JavaScript · Vite · React Router |

## Prerequisites

- PostgreSQL running locally with a database named `yes_officer`
- Docker (Redis runs in a container)
- Python 3.13, Node 22

## Run it

```bash
# 1. Redis
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # (Windows paths)
cp .env.example .env          # fill DATABASE_URL, SECRET_KEY, INTERNAL_SHARED_SECRET
.venv/Scripts/alembic upgrade head
.venv/Scripts/python -m uvicorn api.main:app --port 8000 --reload --reload-dir api

# 3. Celery (two more terminals). On Windows the worker needs --pool=solo.
.venv/Scripts/celery -A api.workers.celery_app worker --pool=solo --loglevel=info
.venv/Scripts/celery -A api.workers.celery_app beat --loglevel=info

# 4. Frontend
cd ../frontend
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm install && npm run dev    # http://localhost:5173
```

The Celery worker and beat are required for: auto-ending polls at their deadline, persisting
results to PostgreSQL, and AI chat analysis (threshold, 10-second interval, and poll-end flushes).

### Pointing the frontend at another backend

All backend locations live in `frontend/src/config/api.js`, driven by `VITE_API_BASE_URL`
(and optionally `VITE_WS_BASE_URL`). Change the env value; nothing else hardcodes a URL.
When the frontend is served from a different origin, add it to the backend's `CORS_ORIGINS`.

### AI analysis

Set `ANTHROPIC_API_KEY` in `backend/.env` to analyse chat with Claude (`LLM_MODEL`, default
`claude-opus-5-5`, low effort, structured output). Without a key a deterministic keyword
stub runs instead, so the whole pipeline works locally.

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest -q     # uses an isolated `test_suite` schema, fakeredis
cd frontend && npm test
```
