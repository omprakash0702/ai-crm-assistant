# AI-CRM — High-Level Design (HLD)

## 1. Purpose

AI-CRM is a pharmaceutical sales CRM that lets medical sales representatives log, query, and act on their HCP (Healthcare Professional) interactions through both a structured form and a natural-language AI chat interface. The system uses LLM-based agents to extract, route, and respond to free-text input, while maintaining strict per-user data isolation.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         BROWSER (React)                         │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────┐  │
│  │ AuthPage │  │ ChatAssistant│  │Interaction │  │Dashboard │  │
│  │(JWT login│  │(AI free text)│  │Form / List │  │SystemPage│  │
│  │ signup)  │  │              │  │            │  │          │  │
│  └────┬─────┘  └──────┬───────┘  └─────┬──────┘  └────┬─────┘  │
│       │               │                │               │        │
│       └───────────────┴────────────────┴───────────────┘        │
│                        JWT Bearer token / HTTPS                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                       FastAPI Backend                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Middleware Stack (outer → inner)                         │  │
│  │  CORSMiddleware → RequestLoggingMiddleware → APIKeyMiddle │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────┐     ┌──────────────────────────────────┐  │
│  │  /auth router   │     │         /api router              │  │
│  │  signup / login │     │  interactions, doctors,          │  │
│  │                 │     │  metrics, followups, chat        │  │
│  └────────┬────────┘     └──────────────┬───────────────────┘  │
│           │                             │                       │
│           │              ┌──────────────▼───────────────────┐  │
│           │              │      Service Layer                │  │
│           │              │  crm_service / ai_service /       │  │
│           │              │  metrics_service / queue_service  │  │
│           │              └──────────────┬───────────────────┘  │
│           │                             │                       │
│  ┌────────▼─────────────────────────────▼───────────────────┐  │
│  │                   Core Layer                              │  │
│  │  auth · security · rate_limit · context · logging        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────┬───────────────────────────────────┬───────────────┘
             │                                   │
┌────────────▼────────────┐        ┌─────────────▼──────────────┐
│       PostgreSQL         │        │           Redis             │
│                          │        │                            │
│  users / doctors /       │        │  Cache (summarize, doctor  │
│  interactions /          │        │  history) · Rate limit     │
│  follow_up_tasks /       │        │  buckets · Cache hit/miss  │
│  llm_calls               │        │  counters · RQ job queue   │
└──────────────────────────┘        └────────────────────────────┘
             │
┌────────────▼────────────┐
│      LLM Providers       │
│                          │
│  Groq (llama-3.1-8b)     │  ← fast tasks: log, edit, extract
│  OpenAI (gpt-4o-mini)    │  ← complex tasks: suggest, summarize
└──────────────────────────┘
```

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | FastAPI 0.136, Python 3.11 |
| Database | PostgreSQL 15 (psycopg2 connection pool) |
| Cache | Redis (portable, in-process on Windows) |
| Task Queue | RQ + SimpleWorker (Windows-compatible) |
| AI Agent | LangGraph `create_react_agent` |
| LLM — Fast | Groq `llama-3.1-8b-instant` |
| LLM — Smart | OpenAI `gpt-4o-mini` |
| Auth — Passwords | passlib + Argon2 |
| Auth — Sessions | python-jose JWT (HS256, 1-hour expiry) |
| Logging | Python `logging` + custom JSON formatter |

---

## 4. Major Components

### 4.1 Frontend (React SPA)

Single-page application served by Vite. No client-side router — page state is managed in `App.jsx` via `useState`. JWT token is stored in `localStorage` and attached to every request via `getJwtHeaders()`. A module-level `apiFetch` wrapper listens for 401 responses and fires an `auth:logout` event to redirect the user to the login screen automatically.

### 4.2 FastAPI Backend

Stateless REST API. Three middleware layers handle CORS, per-request JSON logging, and API-key resolution (legacy). JWT is validated per-request via `HTTPBearer` dependency injection — no session state is kept on the server. All routes return JSON.

### 4.3 AI Pipeline

User messages are classified by a keyword-based router (`app/ai/router.py`) into five task types: **log**, **edit**, **summarize**, **extract**, **suggest**. Each task invokes a LangChain `@tool`-decorated function. The router also performs context injection: if a suggest/summarize/extract message doesn't name a doctor, the last doctor mentioned in the conversation history is appended automatically.

Model selection is separate from routing: fast tasks go to Groq, reasoning tasks (`suggest`) go to OpenAI, with automatic fallback. Every LLM call is retried up to 3 times with a 5-second timeout.

### 4.4 PostgreSQL

Five tables. All user data is scoped by `user_id` — every query includes `WHERE user_id = %s`. A `SimpleConnectionPool` (1–10 connections) is shared across the process. Migrations are applied incrementally via numbered SQL files.

### 4.5 Redis

Serves three purposes simultaneously:
1. **LRU cache** — summarize results and doctor history (TTL 300 s, keys include `user_id`)
2. **Rate limiter** — fixed-window counter per `user_id` (60 req/min on `/chat`)
3. **Job queue** — RQ uses Redis as its broker for async summarization jobs

---

## 5. Authentication Flow

```
Sign Up                              Sign In
─────────────────────────────        ────────────────────────────
User fills form (name, email,        User fills email + password
company, job_title, territory,
password)
        │                                     │
        ▼                                     ▼
POST /auth/signup                    POST /auth/login
  · Argon2-hash password               · Lookup user by email
  · INSERT into users                  · Verify Argon2 hash
  · create_token(user_id)              · create_token(user_id)
        │                                     │
        ▼                                     ▼
  { access_token, user }            { access_token }
        │                                     │
        └──────────────┬──────────────────────┘
                       ▼
             localStorage.setItem('jwt_token', ...)
                       │
                       ▼
            All subsequent requests:
            Authorization: Bearer <token>
                       │
                       ▼
            get_current_user dependency
              · HTTPBearer reads header
              · decode_token → user_id
              · _get_user_by_id → user dict
              · Injected into route handler
```

---

## 6. AI Chat Data Flow

```
User types message
        │
        ▼
ChatAssistant.jsx
  · Appends message to local state
  · Sends: { message, history: last 10 turns }
        │
        ▼
POST /chat  (rate_limit: 60/min)
        │
        ▼
ai_service.chat(message, user_id, history)
  · Sets current_user_id context var
  · _route(message) → task_type
  · run(message, history) →
        │
        ├─ _inject_context(message, history)
        │    · If route ∈ {suggest, summarize, extract}
        │      AND message names no doctor
        │    · Append "(about Dr. X)" from history
        │
        ├─ route == "log"      → log_interaction tool
        ├─ route == "edit"     → edit_interaction tool
        ├─ route == "summarize"→ summarize_text tool
        ├─ route == "extract"  → extract_entities tool
        └─ route == "suggest"  → suggest_next_action tool
                │
                ▼
        LLM call (Groq or OpenAI)
          · 3 retries, 5s timeout each
          · _persist_llm_call → llm_calls table
          · logger.info("llm_call", ...)
                │
                ▼
        Tool result string
                │
                ▼
        { response: "..." }
```

---

## 7. Data Isolation

Every database query is scoped to the authenticated user:

- `interactions WHERE user_id = %s`
- `doctors WHERE user_id = %s`
- `follow_up_tasks WHERE user_id = %s`
- Redis cache keys include `user_id` prefix

LangChain tools receive `user_id` via a `ContextVar` (`current_user_id`) set in `ai_service.chat()` before the agent runs and reset in a `finally` block. Tools cannot access another user's data even if a prompt injection tricks them — the SQL `WHERE user_id = %s` is enforced at the DB layer.

---

## 8. Deployment Topology

### Local Dev
```
localhost:5173  →  Vite dev server (React)
                   (proxies /auth, /chat, /interactions, etc. → localhost:8000)
localhost:8000  →  Uvicorn (FastAPI)
localhost:5432  →  PostgreSQL
localhost:6379  →  Redis (portable binary)
                   python worker.py  (RQ SimpleWorker)
```

### Production (AWS EC2 — Docker Compose)
```
http://13.233.132.223:8000
        │
        ▼
┌─────────────────────────────────────────────────┐
│  Docker Network (ai-crm_default)                │
│                                                 │
│  api (python:3.11-slim)                         │
│    Uvicorn → FastAPI                            │
│      · /auth, /chat, /interactions, ...  →  API │
│      · /assets/*                        →  StaticFiles (frontend/dist) │
│      · /*                               →  index.html (SPA fallback)   │
│                                                 │
│  worker (same image)                           │
│    python worker.py → RQ SimpleWorker          │
│                                                 │
│  redis:7          (internal port 6379)          │
│  db:postgres:15   (internal port 5432)          │
│    init.sql auto-runs on first start            │
└─────────────────────────────────────────────────┘
```

The React frontend is built inside a `node:18-slim` stage of the Dockerfile, and the resulting `dist/` folder is copied into the Python image. FastAPI serves it via `StaticFiles` — no separate frontend server, no CORS issues, single origin.

---

## 9. Key Design Decisions

| Decision | Rationale |
|---|---|
| Keyword-based router (not LLM classifier) | Deterministic, zero-latency, no extra API call |
| Context injection over full message history to LLM | History in LLM input would cost tokens on every turn; injecting only the doctor name is cheap and covers ~90% of follow-up cases |
| ContextVar for user_id in tools | LangChain tools only accept one string argument; can't pass user_id directly |
| SimpleConnectionPool (not async) | psycopg2 is synchronous; matches FastAPI's sync route handlers |
| Redis fails open for rate limiting | If Redis goes down, the API stays up — rate limiting degrades gracefully |
| Argon2 over bcrypt | More memory-hard, recommended by OWASP for new systems |
| Separate `normalize_doctor_name` and `formal_doctor_name` | Dedup key (strips Dr., lowercases) must differ from display value (Dr. Title Case) |
| Frontend served from FastAPI `StaticFiles` | Eliminates CORS, removes need for a separate frontend server or HTTPS split; single Docker image serves everything |
| Multi-stage Docker build (Node → Python) | Frontend is built reproducibly inside Docker; no pre-built `dist/` needed in the repo |
| Single EC2 port (8000) for everything | Simplifies security group rules; no load balancer or reverse proxy needed at this scale |
| `init.sql` auto-run by Postgres container | Schema is applied automatically on first boot; no manual migration step needed after `docker compose up` |
