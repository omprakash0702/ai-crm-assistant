# AI-CRM — Low-Level Design (LLD)

## 1. Database Schema

### 1.1 `users`

| Column            | Type         | Constraints                        |
|-------------------|--------------|------------------------------------|
| id                | SERIAL       | PRIMARY KEY                        |
| name              | TEXT         | NOT NULL                           |
| email             | TEXT         | UNIQUE NOT NULL                    |
| hashed_password   | TEXT         | NOT NULL                           |
| api_key           | TEXT         | UNIQUE (nullable — legacy only)    |
| company           | TEXT         |                                    |
| job_title         | TEXT         |                                    |
| territory         | TEXT         |                                    |
| created_at        | TIMESTAMPTZ  | DEFAULT NOW()                      |

---

### 1.2 `doctors`

| Column              | Type         | Constraints              |
|---------------------|--------------|--------------------------|
| id                  | SERIAL       | PRIMARY KEY              |
| name                | TEXT         | NOT NULL                 |
| user_id             | INTEGER      | NOT NULL, FK → users(id) |
| last_visit          | TIMESTAMPTZ  |                          |
| total_interactions  | INTEGER      | DEFAULT 0                |

**Indexes**
- `uidx_doctors_name_user` — `UNIQUE (LOWER(name), user_id)` — dedup key

**Doctor upsert pattern**
```sql
INSERT INTO doctors (name, user_id) VALUES (%s, %s)
ON CONFLICT (LOWER(name), user_id)
DO UPDATE SET name = EXCLUDED.name
RETURNING id
```
`LOWER(name)` is the dedup key; the stored `name` is the formal display value (`Dr. Title Case`).

---

### 1.3 `interactions`

| Column               | Type         | Constraints                              |
|----------------------|--------------|------------------------------------------|
| id                   | SERIAL       | PRIMARY KEY                              |
| doctor_name          | TEXT         | NOT NULL                                 |
| notes                | TEXT         |                                          |
| interaction_type     | TEXT         | e.g. `'Call'`, `'Visit'`, `'Meeting'`   |
| attendees            | TEXT         |                                          |
| products_discussed   | TEXT         |                                          |
| sentiment            | TEXT         | `'Positive'`, `'Neutral'`, `'Negative'` |
| follow_up            | TEXT         |                                          |
| date_time            | TIMESTAMPTZ  | DEFAULT NOW()                            |
| user_id              | INTEGER      | NOT NULL, FK → users(id)                 |
| doctor_id            | INTEGER      | NOT NULL, FK → doctors(id)               |

**Indexes**
- `idx_interactions_user` — `(user_id)`
- `idx_interactions_doctor` — `(doctor_id)`

---

### 1.4 `follow_up_tasks`

| Column      | Type        | Constraints                              |
|-------------|-------------|------------------------------------------|
| id          | SERIAL      | PRIMARY KEY                              |
| doctor_id   | INTEGER     | NOT NULL, FK → doctors(id)               |
| task        | TEXT        | NOT NULL                                 |
| due_date    | DATE        |                                          |
| status      | TEXT        | DEFAULT `'pending'`                      |
| user_id     | INTEGER     | NOT NULL, FK → users(id)                 |

---

### 1.5 `llm_calls`

| Column       | Type         | Constraints              |
|--------------|--------------|--------------------------|
| id           | SERIAL       | PRIMARY KEY              |
| user_id      | INTEGER      | FK → users(id)           |
| model        | TEXT         | e.g. `'groq'`, `'openai'` |
| latency_ms   | INTEGER      |                          |
| cost_usd     | NUMERIC      |                          |
| tokens_used  | INTEGER      |                          |
| created_at   | TIMESTAMPTZ  | DEFAULT NOW()            |

**Indexes**
- `idx_llm_calls_user` — `(user_id)`
- `idx_llm_calls_created` — `(created_at)`

---

### 1.6 Migration History

| File                          | What it does                                                        |
|-------------------------------|---------------------------------------------------------------------|
| `setup_db.sql`                | Initial `interactions` table                                        |
| `migrate_db.sql`              | Adds structured columns to `interactions`                           |
| `migrate_auth.sql`            | Creates `users` table, adds `user_id` FK to all tables             |
| `migrate_extend.sql`          | Creates `doctors` and `follow_up_tasks` tables, adds `doctor_id`   |
| `migrate_indexes.sql`         | NOT NULL constraints + index creation                               |
| `migrate_jwt_auth.sql`        | Adds `email`, `hashed_password` to `users`                         |
| `migrate_llm_calls.sql`       | Creates `llm_calls` table                                           |
| `migrate_sales_profile.sql`   | Adds `company`, `job_title`, `territory`; relaxes `api_key NOT NULL` |

---

## 2. API Endpoints

Base prefix: `/api` — all routes below are relative to that.
Auth dependencies: `get_current_user` (JWT) or `rate_limit` (JWT + rate window).

### Auth — `/auth` (no prefix)

| Method | Path           | Auth | Request body                                                            | Response                                      |
|--------|----------------|------|-------------------------------------------------------------------------|-----------------------------------------------|
| POST   | /auth/signup   | —    | `name, email, password, company, job_title?, territory?`                | `{access_token, token_type, user: {id, name, email, company, job_title}}` |
| POST   | /auth/login    | —    | `email, password`                                                       | `{access_token, token_type}`                  |

### Interactions

| Method | Path                           | Auth            | Request body / params           | Response                           |
|--------|--------------------------------|-----------------|---------------------------------|------------------------------------|
| GET    | /interactions                  | get_current_user | —                               | Array of interaction objects       |
| POST   | /log-structured-interaction    | get_current_user | `StructuredInteractionRequest`  | `{message, id}`                    |
| POST   | /log-interaction               | get_current_user | `{doctor_name, notes}`          | `{message, id}`                    |
| POST   | /edit-interaction              | get_current_user | `{id, notes}`                   | `{message, id}` or 404             |

### AI Chat

| Method | Path      | Auth       | Request body                    | Response          |
|--------|-----------|------------|---------------------------------|-------------------|
| POST   | /chat     | rate_limit | `{message, history?: [...] }`   | `{response: str}` |

### Async Jobs

| Method | Path              | Auth            | Body / param   | Response                           |
|--------|-------------------|-----------------|----------------|------------------------------------|
| POST   | /summarize-async  | get_current_user | `{text}`       | `{job_id}`                         |
| GET    | /job/{job_id}     | get_current_user | path param     | `{status, result}` or 404          |

### Metrics

| Method | Path                    | Auth            | Response                                                       |
|--------|-------------------------|-----------------|----------------------------------------------------------------|
| GET    | /metrics/summary        | get_current_user | `{total_interactions, total_doctors, avg_interactions_per_doctor}` |
| GET    | /metrics/top-doctors    | get_current_user | Array of `{name, interaction_count}`                           |
| GET    | /metrics/sentiment-trend| get_current_user | Array of `{date, positive, neutral, negative}`                 |
| GET    | /metrics/followups      | get_current_user | Array of follow-up task objects                                |
| GET    | /metrics/system         | get_current_user | `{total_llm_calls, avg_latency_ms, total_cost_usd, model_usage: {groq, openai}, cache_hits, cache_misses}` |

### Doctors

| Method | Path                       | Auth            | Body / param             | Response                    |
|--------|----------------------------|-----------------|--------------------------|-----------------------------|
| GET    | /doctors                   | get_current_user | —                        | Array of doctor objects     |
| POST   | /doctors                   | get_current_user | `{name}`                 | Created doctor object       |
| GET    | /doctors/{doctor_id}       | get_current_user | path param               | Doctor object or 404        |
| GET    | /doctor/{name}             | get_current_user | path param (string)      | Doctor profile or 404       |
| GET    | /doctor/{name}/timeline    | get_current_user | path param (string)      | Timeline array or 404       |

### Follow-ups

| Method | Path                          | Auth            | Body / param                         | Response                     |
|--------|-------------------------------|-----------------|--------------------------------------|------------------------------|
| POST   | /followups                    | get_current_user | `{doctor_id, task, due_date, status}` | Created follow-up object    |
| GET    | /doctors/{doctor_id}/followups| get_current_user | path param                           | Array of follow-up objects  |
| PATCH  | /followups/{followup_id}      | get_current_user | `{status}`                           | `{message, id}` or 404      |
| DELETE | /followups/{followup_id}      | get_current_user | path param                           | `{message, id}` or 404      |

---

## 3. Backend Module Map

### `main.py`
- Creates `FastAPI` app
- Registers middleware (outermost first): `CORSMiddleware` → `RequestLoggingMiddleware` → `APIKeyMiddleware`
- Mounts `auth_router` at `/auth`, main `router` at `/api`
- CORS origins: `http://localhost:5173`; credentials: `true`; headers: `Content-Type, Authorization, X-API-Key`

### `app/core/`

| File               | Key exports / purpose                                                         |
|--------------------|-------------------------------------------------------------------------------|
| `config.py`        | Reads DB_* env vars; exposes `DB_CONFIG` dict                                |
| `context.py`       | `current_user_id: ContextVar[int]` — thread-safe user_id for LangChain tools |
| `security.py`      | `hash_password`, `verify_password`, `create_token`, `decode_token`           |
| `auth.py`          | `get_current_user` (JWT dependency), `APIKeyMiddleware`, `_get_user_by_id`   |
| `rate_limit.py`    | `rate_limit` FastAPI dependency — 60 req/min per user via Redis INCR          |
| `redis_client.py`  | `get_cache`, `set_cache` (TTL=300 s), `get_cache_stats`                      |
| `logging_config.py`| `JSONFormatter`, `RequestLoggingMiddleware`, `setup_logging`                  |

#### `security.py` — function signatures
```python
hash_password(password: str) -> str
verify_password(plain: str, hashed: str) -> bool
create_token(user_id: int) -> str          # HS256, 1-hour expiry
decode_token(token: str) -> int            # raises HTTP 401 on bad token
```

#### `auth.py` — key functions
```python
_get_user_by_id(user_id: int) -> dict | None
_get_user_by_email(email: str) -> dict | None
get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict
```

#### `rate_limit.py` — algorithm
```
key  = f"rate:{user_id}:{int(time.time() // 60)}"
count = INCR key
if count == 1: EXPIRE key 60
if count > 60: raise HTTP 429
return user dict
```

### `app/db/`

| File            | Key exports                                                                  |
|-----------------|------------------------------------------------------------------------------|
| `connection.py` | `SimpleConnectionPool(1, 10)`, `get_connection()`, `release_connection()`   |
| `queries.py`    | `get_or_create_doctor`, `update_doctor_stats`, `fetch_doctor_history`, `is_duplicate` |

#### `queries.py` — function signatures
```python
get_or_create_doctor(normalized_name: str, user_id: int) -> int
    # INSERT ... ON CONFLICT DO UPDATE; returns doctor_id

update_doctor_stats(doctor_id: int) -> None
    # UPDATE SET last_visit=NOW(), total_interactions = total_interactions + 1

fetch_doctor_history(doctor_name: str, user_id: int) -> list[dict]
    # SELECT last 5 interactions WHERE doctor_name ILIKE %doctor_name%

is_duplicate(new_notes: str, doctor_name: str, user_id: int) -> bool
    # SequenceMatcher ratio > 0.85 against last 5 notes for same doctor
```

### `app/models/schemas.py`

```python
class StructuredInteractionRequest(BaseModel):
    doctor_name: str                # max 200 chars, required
    interaction_type: str           # max 50 chars
    notes: str                      # max 2000 chars
    attendees: Optional[str]
    products_discussed: Optional[str]
    sentiment: Optional[str]        # Positive | Neutral | Negative
    follow_up: Optional[str]
    date_time: Optional[datetime]

class LogInteractionRequest(BaseModel):
    doctor_name: str
    notes: str

class EditInteractionRequest(BaseModel):
    id: int
    notes: str

class HistoryMessage(BaseModel):
    role: str   # "user" | "agent"
    text: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[HistoryMessage]] = None

class SummarizeRequest(BaseModel):
    text: str

class DoctorCreate(BaseModel):
    name: str

class FollowUpCreate(BaseModel):
    doctor_id: int
    task: str
    due_date: Optional[str]
    status: Optional[str] = "pending"

class FollowUpUpdate(BaseModel):
    status: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str                   # min 8 chars (validated)
    company: Optional[str]
    job_title: Optional[str]
    territory: Optional[str]

class LoginRequest(BaseModel):
    email: str
    password: str
```

### `app/auth/router.py`

```
POST /auth/signup
  1. Hash password with Argon2
  2. INSERT INTO users (name, email, hashed_password, company, job_title, territory)
  3. create_token(new_user_id)
  4. Return {access_token, token_type:"bearer", user:{id,name,email,company,job_title}}
  → 409 if email already exists
  → 201 on success

POST /auth/login
  1. _get_user_by_email(email) → 401 if not found
  2. verify_password(plain, hashed) → 401 if wrong
  3. create_token(user_id)
  4. Return {access_token, token_type:"bearer"}
```

### `app/ai/`

| File             | Purpose                                                             |
|------------------|---------------------------------------------------------------------|
| `client.py`      | Groq LangChain `ChatGroq` instance; system prompt; `invoke()` wrapper |
| `model_router.py`| Model selection, retry, timeout, cost tracking, DB persistence      |
| `router.py`      | Keyword router, context injection, `run()` dispatcher              |
| `tools.py`       | 5 `@tool` functions; `agent_graph` (LangGraph ReAct)               |
| `validators.py`  | Sentinel validators used inside tools                               |

#### `model_router.py` — key functions
```python
route_model(task: str) -> str
    # "suggest" → "openai"; everything else → "groq"

invoke_routed(prompt: str, task: str = "log") -> str
    # 1. route_model(task) → provider
    # 2. ThreadPoolExecutor: call LLM with 5s timeout per attempt
    # 3. Retry up to 3 times (groq first, then openai fallback on error)
    # 4. _log_cost(response) — compute cost from token counts
    # 5. _persist_llm_call(provider, latency_ms, cost_usd, tokens) — INSERT llm_calls
    # 6. Return response.content

_persist_llm_call(model: str, latency_ms: int, cost_usd: float, tokens: int) -> None
    # Reads current_user_id ContextVar; silently skips if not set
    # INSERT INTO llm_calls (user_id, model, latency_ms, cost_usd, tokens_used)
```

**Cost rates**
| Provider | Input (per M tokens) | Output (per M tokens) |
|----------|----------------------|-----------------------|
| Groq     | $0.05                | $0.08                 |
| OpenAI   | $0.15                | $0.60                 |

#### `router.py` — keyword sets
```python
_EDIT_WORDS      = ("update", "edit", "change", "correct", "fix", "modify")
_SUMMARIZE_WORDS = ("summarize", "summary", "shorten", "condense", "brief", "all interaction")
_EXTRACT_WORDS   = ("extract", "pull out", "identify", "list the", "what doctor",
                    "which medicine", "what product")
_SUGGEST_WORDS   = ("next step", "what should i do", "suggest", "recommend",
                    "follow up", "follow-up", "what now", "advice", "plan",
                    "what next", "what to do", "should i do")
```

**`_route(text)` decision tree**
```
1. text matches ^(regarding|about)\s+dr\.?\s+ → "suggest"
2. any(_EDIT_WORDS) AND \b\d+\b in text       → "edit"
3. any(_SUMMARIZE_WORDS)                       → "summarize"
4. any(_EXTRACT_WORDS)                         → "extract"
5. any(_SUGGEST_WORDS)                         → "suggest"
6. default                                     → "log"
```

**Context injection (`_inject_context`)**
```
if text already names a doctor → return unchanged
last = _last_doctor_in_history(history)
if last → return f"{text} (about {last})"
else    → return text unchanged
```
Context is injected only for `suggest`, `summarize`, `extract` — never `log` or `edit`.

#### `tools.py` — tool signatures and logic

```python
@tool
def log_interaction(text: str) -> str:
    # 1. LLM prompt → 5-line parse: Doctor, Type, Sentiment, Follow-up, Summary
    # 2. detect_interaction_type(text) fallback if LLM Type is missing
    # 3. formal_doctor_name(raw) for display; normalize_doctor_name for dedup
    # 4. is_duplicate() check → return early if duplicate
    # 5. get_or_create_doctor(normalized, user_id) → doctor_id
    # 6. INSERT INTO interactions (doctor_name, notes, interaction_type, sentiment, follow_up, user_id, doctor_id)
    # 7. update_doctor_stats(doctor_id)

@tool
def edit_interaction(text: str) -> str:
    # 1. Parse integer ID from text (\b\d+\b)
    # 2. LLM → extract new note text
    # 3. UPDATE interactions SET notes=%s WHERE id=%s AND user_id=%s

@tool
def summarize_text(text: str) -> str:
    # 1. extract_name_simple(text) → doctor name
    # 2. cache_key = f"summary:{user_id}:{doctor_name}"
    # 3. get_cache(key) → return cached if hit
    # 4. fetch_doctor_history(doctor_name, user_id) → recent notes
    # 5. LLM summarize (invoke_routed, task="summarize")
    # 6. set_cache(key, result, ttl=300)

@tool
def extract_entities(text: str) -> str:
    # LLM prompt → extract Doctor, Products/Medicines, Location, Date from text
    # task="extract"

@tool
def suggest_next_action(text: str) -> str:
    # 1. extract_name_simple(text) → doctor name
    # 2. fetch_doctor_history(doctor_name, user_id) → last 5 notes
    # 3. LLM → recommend next CRM action given history
    # 4. task="suggest" → routed to OpenAI gpt-4o-mini
```

### `app/services/`

| File                  | Key functions                                                        |
|-----------------------|----------------------------------------------------------------------|
| `crm_service.py`      | All DB read/write for interactions, doctors, follow-ups, metrics    |
| `ai_service.py`       | `chat()` — sets ContextVar, calls `router.run()`, logs result       |
| `metrics_service.py`  | `get_system_metrics()` — aggregates llm_calls + Redis cache stats   |
| `queue_service.py`    | `enqueue_summarize()`, `get_job_result()` via RQ + Redis            |

#### `ai_service.chat()` flow
```python
def chat(message: str, user_id: int, history=None) -> str:
    token = current_user_id.set(user_id)
    try:
        return router.run(message, history)
    finally:
        current_user_id.reset(token)
```

#### `crm_service.py` — key function signatures
```python
get_interactions(user_id: int) -> list[dict]
    # SELECT * FROM interactions WHERE user_id=%s ORDER BY date_time DESC LIMIT 20

log_structured_interaction(doctor_name, interaction_type, notes, attendees,
                           products_discussed, sentiment, follow_up, date_time, user_id) -> int
    # formal_doctor_name(doctor_name) → normalized insert

log_interaction_basic(doctor_name: str, notes: str, user_id: int) -> int

edit_interaction_basic(interaction_id: int, notes: str, user_id: int) -> bool

get_metrics_summary(user_id: int) -> dict
    # {total_interactions, total_doctors, avg_interactions_per_doctor}

get_top_doctors(user_id: int) -> list[dict]
    # SELECT doctor_name, COUNT(*) GROUP BY doctor_name ORDER BY COUNT DESC LIMIT 5

get_sentiment_trend(user_id: int) -> list[dict]
    # Daily counts of Positive/Neutral/Negative for last 30 days

get_doctor_profile(name: str, user_id: int) -> dict | None
get_doctor_timeline(name: str, user_id: int) -> list | None
get_all_doctors(user_id: int) -> list[dict]
create_doctor_record(name: str, user_id: int) -> dict
get_doctor_by_id(doctor_id: int, user_id: int) -> dict | None
create_followup(doctor_id, task, due_date, status, user_id) -> dict
get_followups_by_doctor(doctor_id: int, user_id: int) -> list[dict]
update_followup_status(followup_id: int, status: str, user_id: int) -> bool
delete_followup(followup_id: int, user_id: int) -> bool
```

### `app/utils/text.py`

```python
formal_doctor_name(name: str) -> str
    # strips leading "Dr." / "Dr", title-cases remaining words, prepends "Dr. "
    # e.g. "dr. john smith" → "Dr. John Smith"

normalize_doctor_name(name: str) -> str
    # formal_doctor_name(name).lower() stripped of "dr. " prefix
    # used as the dedup key passed to get_or_create_doctor()

extract_name_simple(text: str) -> str | None
    # regex: \bDr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)
    # returns formal_doctor_name(match) or None

detect_interaction_type(text: str) -> str
    # keyword scan → "Call" | "Visit" | "Meeting" (default)
    # Call keywords: called, call, phone, phoned, rang, dialled, dialed
    # Visit keywords: visited, visit, clinic, in-person, stopped by, dropped by
```

---

## 4. Frontend Component Tree

```
App.jsx
│  state: authed (bool), page ("chat"|"dashboard"|"system")
│  effect: listens for "auth:logout" event → setAuthed(false)
│
├─ AuthPage.jsx (rendered when !authed)
│    state: tab ("login"|"signup"), form fields, error, loading
│    POST /auth/login  → localStorage.setItem('jwt_token', ...)
│    POST /auth/signup → localStorage.setItem('jwt_token', ...)
│
└─ (when authed)
     Nav.jsx
     │  props: page, setPage, onLogout
     │  renders: Chat | Dashboard | System tabs + Logout button
     │
     ├─ ChatAssistant.jsx      (page === "chat")
     │    state: messages[], input, loading
     │    POST /api/chat with {message, history: last 10 msgs}
     │    onSuccess prop → triggers interaction list refresh
     │
     ├─ InteractionForm.jsx    (page === "chat", right panel)
     │    state: form fields (doctor_name, type, notes, etc.)
     │    POST /api/log-structured-interaction
     │
     ├─ InteractionList.jsx    (page === "chat", right panel)
     │    state: interactions[], loading
     │    GET /api/interactions
     │    refreshKey prop to re-fetch after new log
     │
     ├─ Dashboard.jsx          (page === "dashboard")
     │    state: summary, topDoctors, error
     │    GET /api/metrics/summary + /api/metrics/top-doctors (parallel)
     │
     └─ SystemPage.jsx         (page === "system")
          state: metrics, summary, error
          GET /api/metrics/system + /api/metrics/summary (parallel)
          Displays: LLM usage, cache stats, auth info, model routing, infra
```

### `src/api.js` — exported utilities
```js
export const API = 'http://localhost:8000/api'

export function getHeaders()    // { 'Content-Type': 'application/json', 'X-API-Key': ... }
export function getJwtHeaders() // { 'Content-Type': 'application/json', 'Authorization': 'Bearer <token>' }

export async function apiFetch(url, options = {}) {
  const res = await fetch(url, options)
  if (res.status === 401) {
    localStorage.removeItem('jwt_token')
    window.dispatchEvent(new Event('auth:logout'))
  }
  return res
}
```

---

## 5. Key Algorithms

### 5.1 Doctor Name Pipeline

```
Raw input (any case)
       │
       ▼
formal_doctor_name()
  strip leading "dr." / "Dr" (case-insensitive)
  title-case each word
  prepend "Dr. "
       │
       ├──→ stored in interactions.doctor_name  (display)
       │
       ▼
normalize_doctor_name()   [= formal.lower().removeprefix("dr. ")]
       │
       ▼
get_or_create_doctor(normalized, user_id)
  INSERT ... ON CONFLICT (LOWER(name), user_id) DO UPDATE SET name=EXCLUDED.name
       │
       ▼
  doctor_id returned
```

Both the structured form path and the chat tool path go through this pipeline, ensuring a single canonical doctor record regardless of input casing or "Dr." prefix variation.

### 5.2 LLM Routing & Retry

```
invoke_routed(prompt, task)
       │
       ▼
route_model(task)  →  "groq" | "openai"
       │
       ├── groq  → llama-3.1-8b-instant
       └── openai → gpt-4o-mini
              │
              ▼
        ThreadPoolExecutor.submit(llm.invoke, prompt)
        future.result(timeout=5)
              │
         ┌────┴──────────────────┐
         │  success              │  exception or timeout
         ▼                       ▼
   extract tokens          retry (up to 3 attempts)
   _log_cost()             if all fail → fallback provider
   _persist_llm_call()
         │
         ▼
   response.content  (string)
```

### 5.3 Chat Context Injection

```
user sends message M with history H
       │
       ▼
_route(M)  →  task_type
       │
       ├── task_type ∈ {suggest, summarize, extract}
       │         │
       │         ▼
       │   _inject_context(M, H)
       │     └─ extract_name_simple(M) or dr\.?\s+\w+ ?
       │           ├─ yes → return M unchanged
       │           └─ no  → _last_doctor_in_history(H)
       │                       ├─ found → return M + " (about Dr. X)"
       │                       └─ none  → return M unchanged
       │
       └── task_type ∈ {log, edit}
                 return M unchanged  ← IMPORTANT: prevents stamping wrong doctor
```

`_last_doctor_in_history` scans history newest-first, matching:
1. Pattern `(?:for|with|about)\s+(Dr\.?\s+[A-Za-z]+)` in agent replies
2. Plain `extract_name_simple()` against all messages

### 5.4 Duplicate Interaction Detection

```python
is_duplicate(new_notes, doctor_name, user_id):
    rows = fetch_doctor_history(doctor_name, user_id)  # last 5 interactions
    for row in rows:
        ratio = SequenceMatcher(None, new_notes.lower(), row["notes"].lower()).ratio()
        if ratio > 0.85:
            return True
    return False
```

Called inside `log_interaction` tool before every INSERT.

### 5.5 Redis Rate Limiting

```
key = f"rate:{user_id}:{floor(unix_time / 60)}"
n   = INCR key
if n == 1: EXPIRE key 60        # start window TTL on first request
if n > 60: raise HTTP 429       # fixed-window 60 req/min
```

Rate limit is applied only to `POST /chat`. Redis failure is non-blocking (fail-open): if Redis is unavailable the counter can't be read, so the request proceeds.

### 5.6 Cache Strategy (Redis)

```
get_cache(key):
    val = redis.get(key)
    if val is None:
        INCR "sys:cache_misses"
        return None
    INCR "sys:cache_hits"
    return json.loads(val)

set_cache(key, value, ttl=300):
    redis.setex(key, ttl, json.dumps(value))
```

Cache keys include `user_id` to enforce data isolation:
- `summary:{user_id}:{doctor_name}` — summarize results
- `history:{user_id}:{doctor_name}` — doctor history (used in suggest tool)

---

## 6. Data Flows

### 6.1 Structured Form Interaction Log

```
User fills InteractionForm → POST /api/log-structured-interaction
       │
       ▼
routes.py: log_structured_interaction()
       │
       ▼
crm_service.log_structured_interaction()
  formal  = formal_doctor_name(doctor_name)
  norm    = normalize_doctor_name(formal)
  doc_id  = get_or_create_doctor(norm, user_id)
  INSERT INTO interactions (doctor_name=formal, interaction_type, notes, ..., doctor_id, user_id)
  update_doctor_stats(doc_id)
       │
       ▼
{"message": "Interaction logged", "id": new_id}
       │
       ▼
InteractionList re-fetches via refreshKey prop change
```

### 6.2 Chat → Log Interaction

```
User: "Called Dr. Sharma, discussed Metformin"
       │
       ▼
POST /api/chat {message, history}
  rate_limit dep → get_current_user → check Redis counter
       │
       ▼
ai_service.chat(message, user_id, history)
  current_user_id.set(user_id)
  router.run(message, history)
       │
       ▼
_route(message) → "log"   (no keyword match → default)
enriched = message         (no context injection for log)
log_interaction.invoke(enriched)
       │
       ▼
LLM prompt → 5-line parse:
  Doctor:    Dr. Sharma
  Type:      Call
  Sentiment: Positive
  Follow-up: Send samples
  Summary:   Discussed Metformin benefits

formal_doctor_name("Dr. Sharma") → "Dr. Sharma"
normalize → "sharma"
get_or_create_doctor("sharma", user_id) → doctor_id
is_duplicate() → False
INSERT interactions (interaction_type="Call", doctor_name="Dr. Sharma", ...)
update_doctor_stats(doctor_id)
       │
       ▼
{"response": "Logged interaction for Dr. Sharma (Call). Follow-up: Send samples"}
```

### 6.3 Chat → Suggest (with Context Injection)

```
History contains: "...logged for Dr. Cooper..."
User: "next step?"
       │
       ▼
_route("next step?") → "suggest"
_inject_context("next step?", history)
  extract_name_simple("next step?") → None
  _last_doctor_in_history(history)
    → scans: finds "logged for Dr. Cooper"
    → returns "Dr. Cooper"
  enriched = "next step? (about Dr. Cooper)"
       │
       ▼
suggest_next_action.invoke("next step? (about Dr. Cooper)")
  extract_name_simple → "Dr. Cooper"
  fetch_doctor_history("Dr. Cooper", user_id) → last 5 notes
  invoke_routed(prompt, task="suggest") → OpenAI gpt-4o-mini
       │
       ▼
{"response": "Based on your last visit with Dr. Cooper ..."}
```

### 6.4 Summarize with Redis Cache

```
User: "summarize Dr. Patel"
       │
       ▼
_route → "summarize"
_inject_context → has doctor, unchanged
summarize_text.invoke("summarize Dr. Patel")
  doctor = extract_name_simple(text) → "Dr. Patel"
  key    = f"summary:{user_id}:dr. patel"
  cached = get_cache(key)
       │
  ┌────┴─────────────────────────────┐
  │ cache hit                        │ cache miss
  ▼                                  ▼
incr sys:cache_hits           incr sys:cache_misses
return cached string          fetch_doctor_history(doctor, user_id)
                              invoke_routed(prompt, task="summarize") → Groq
                              set_cache(key, result, ttl=300)
                              return result
```

### 6.5 Async Summarize via RQ

```
POST /api/summarize-async {text}
       │
       ▼
queue_service.enqueue_summarize(text)
  q = Queue(connection=redis_conn)
  job = q.enqueue(summarize_text.invoke, text)
  return job.id
       │
       ▼
{"job_id": "abc123"}

--- Worker process (worker.py) ---
SimpleWorker([queue]).work(burst=True)
  dequeue job → summarize_text.invoke(text)
  store result in Redis job key

GET /api/job/{job_id}
  queue_service.get_job_result(job_id)
  job = Job.fetch(job_id, connection=conn)
  return {status: job.get_status(), result: job.result}
```

---

## 7. Middleware Stack

Middleware is applied outermost-first (request passes through in order, response passes back in reverse):

```
Request → CORSMiddleware
        → RequestLoggingMiddleware   (logs method, path, user_id, latency_ms as JSON)
        → APIKeyMiddleware            (reads X-API-Key; populates request.state.user for legacy routes)
        → Route Handler
        → APIKeyMiddleware
        → RequestLoggingMiddleware
        → CORSMiddleware → Response
```

`RequestLoggingMiddleware` extracts `user_id` from `request.state.user` if set (legacy API key path) or leaves it null; the JWT path sets user via `Depends(get_current_user)` inside the route, so middleware sees `null` for JWT users. JWT user_id appears only in the `logger.info("llm_call", ...)` calls emitted from within service functions.

---

## 8. Environment Variables

| Variable       | Used in             | Default (dev)                |
|----------------|---------------------|------------------------------|
| `DB_NAME`      | `app/core/config.py` | —                           |
| `DB_USER`      | `app/core/config.py` | —                           |
| `DB_PASSWORD`  | `app/core/config.py` | —                           |
| `DB_HOST`      | `app/core/config.py` | `localhost`                 |
| `DB_PORT`      | `app/core/config.py` | `5432`                      |
| `JWT_SECRET`   | `app/core/security.py` | `"change-me-in-production"` |
| `GROQ_API_KEY` | `app/ai/client.py` | —                            |
| `OPENAI_API_KEY` | `app/ai/model_router.py` | —                       |
| `REDIS_URL`    | `app/core/redis_client.py` | `redis://localhost:6379` |

---

## 9. Local Dev Process Map

```
npm run dev          → Vite at :5173  (frontend)
uvicorn main:app     → FastAPI at :8000
python worker.py     → RQ SimpleWorker (async jobs)
redis-server         → Redis at :6379 (portable binary on Windows)
PostgreSQL           → :5432
```

All cross-origin requests from `:5173` → `:8000` are handled by `CORSMiddleware` with `allow_credentials=True` and explicit `Authorization` header allowance.
