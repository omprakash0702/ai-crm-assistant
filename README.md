# AI CRM Assistant

AI CRM Assistant is a field sales tool built for pharmaceutical sales representatives. The core idea is that a rep should be able to open a chat window and say "met Dr. Patel, discussed Metformin, he was interested" and have that automatically parsed, classified, and stored — without filling in a form. The same interface lets them ask what to do next with a specific doctor, get a quick summary of past interactions, or extract structured details from rough notes.

---

## What the Project Does

The application has two primary surfaces: a chat assistant and a structured dashboard. The chat assistant accepts free-text input and routes it to one of five AI-backed operations — logging a new interaction, editing an existing one, summarizing a doctor's history, extracting entities from text, or suggesting a next action. The dashboard shows aggregate metrics (total interactions, top doctors by volume), and clicking any doctor name opens a modal that pulls their full interaction timeline and formats every note into a clean formal sentence using a separate AI call.

Behind the chat is a FastAPI backend with PostgreSQL for storage, Redis for caching and lightweight counters, and RQ for asynchronous job processing. Authentication uses JWT tokens with Argon2 password hashing.

---

## How AI Is Used

The system uses LangChain and LangGraph to define five tools, each decorated with `@tool` and registered in a `create_react_agent` graph. However, it is important to be precise about what "agentic" means here: the LLM does not decide which tool to call. Routing is handled entirely by a deterministic Python keyword router before any LLM is involved. Once the route is decided, the corresponding tool is called directly. The agent graph is initialized and the tools are properly registered, but the agentic loop (where the model reasons about which tool to use next) is not the active dispatch path.

Within each tool, the LLM does real work. The `log_interaction` tool sends the user's raw message to Groq and asks it to extract a structured record: doctor name, interaction type, sentiment, products discussed, and a follow-up suggestion. That structured output is then written to PostgreSQL. The `suggest_next_action` tool fetches the doctor's actual interaction history from the database and asks the LLM for one specific, grounded next step — the model is not inventing context, it is reasoning over real records. The `summarize_text` and `extract_entities` tools similarly ground the LLM in database-fetched or user-provided text.

There is also a separate AI path that is not part of the chat at all: when a user opens the doctor detail modal in the dashboard, the frontend fetches the timeline and then fires a single `POST /format-notes` request. The backend sends all notes from that timeline in one batched LLM call, prefixing each note with its interaction type (e.g., `[Call]`, `[Visit]`, `[Meeting]`), and the model returns one clean formal sentence per note. This keeps the dashboard readable without requiring the rep to write formal notes in the field.

---

## How Agentic Is It

Honestly: partially. The project uses the LangGraph and LangChain infrastructure correctly — tools are defined, the agent is created, context injection works — but the routing decision is made by Python, not by the model. This is a deliberate trade-off: keyword routing is deterministic, zero-latency, and fully predictable. If a sales rep types "summarize Dr. Sharma's notes", you do not want the system to occasionally decide to log instead. The keyword router makes that impossible.

Where the system is genuinely AI-driven is inside the tools themselves. The `log_interaction` tool does real structured extraction from natural language. The `suggest_next_action` tool produces personalized recommendations from actual history. The batch formatting in the dashboard runs an LLM call that rewrites raw field notes into professional sentences. These are all cases where a rule-based approach would fail or be too brittle.

---

## Message Routing in Detail

Every chat message passes through `_route()` in `app/ai/router.py` before touching the LLM. The router checks the lowercased message for keyword patterns and returns a route label. Messages containing "update", "edit", "change", or a bare interaction ID are routed to `edit_interaction`. Messages containing "summarize" or "summary" go to `summarize_text`. Messages with "extract", "identify", "who", "what product", or "where" go to `extract_entities`. Messages with "suggest", "recommend", "what should", "next step", or "plan" go to `suggest_next_action`. Everything else defaults to `log_interaction`.

For the suggest, summarize, and extract routes, the router also scans the last ten messages in the conversation history for the most recently mentioned doctor name. If found, it appends `(about Dr. X)` to the user's message before passing it to the tool. This lets the rep say "what should I do next?" without repeating the doctor's name, and the tool still has enough context to fetch the right records.

---

## Dual-Model Routing and Resilience

Not all tasks need the same model. Fast, straightforward tasks — logging, editing, summarizing, extracting — use Groq's `llama-3.1-8b-instant`, which responds in under a second. Tasks that require more reasoning — specifically `suggest_next_action` — use OpenAI's `gpt-4o-mini`.

Every LLM call goes through `invoke_routed()` in `app/ai/model_router.py`, which retries up to three times with a five-second timeout per attempt. If all retries fail on one provider, the call automatically falls back to the other. Retry counts and final failure counts are tracked in Redis and exposed via `/metrics/system`, so you can see how often the system had to recover without changing any of the retry behavior itself.

---

## Why These Technologies

FastAPI was chosen because it is fast to develop with, generates automatic OpenAPI docs, and handles dependency injection cleanly — the `Depends(get_current_user)` pattern keeps auth out of every route handler. PostgreSQL is the primary store because the data is relational (users, doctors, interactions, follow-ups all reference each other by foreign key) and SQL makes the aggregate queries for the dashboard straightforward.

Redis serves two roles: it caches expensive database reads for frequently visited doctor profiles, and it acts as a lightweight counter store for metrics (cache hits/misses, retry counts, failed requests, total jobs enqueued). Using Redis for metrics avoids adding a column to PostgreSQL for every counter.

RQ (Redis Queue) handles async jobs — right now, the summarize-async endpoint. On Windows, RQ's standard forking worker does not work, so the project uses `SimpleWorker`, which runs jobs in the same process. This is a known limitation noted in the configuration.

Groq was chosen for its inference speed on the `llama-3.1-8b-instant` model — it is genuinely fast enough for real-time chat. OpenAI's `gpt-4o-mini` was added for the suggestion route because it produces more coherent, context-sensitive recommendations for the next-action use case. Argon2 was chosen for password hashing because it is the current best practice (winner of the Password Hashing Competition) and substantially more resistant to GPU cracking than bcrypt. JWT HS256 was chosen for stateless auth because the application is single-server and does not need the complexity of asymmetric keys.

React with Vite and Tailwind was chosen for the frontend because Vite's dev server is fast and Tailwind keeps the component styling consistent without a separate CSS file per component. There is no client-side router; navigation is handled with React state, which is sufficient for an application of this scope.

---

## Why This Project Is Useful

Pharmaceutical sales representatives interact with dozens of doctors each week. They need to log those interactions quickly, remember context before a follow-up visit, and have some way of knowing which doctors to prioritize. Existing CRM tools require them to fill in forms field by field, which reps often skip or do after the fact when details are already fuzzy.

The chat interface removes that friction. A rep can type a sentence on their phone right after leaving the clinic, and the system handles parsing, classification, sentiment analysis, and follow-up extraction automatically. The suggestion tool means they do not have to remember which doctor was last visited four weeks ago and what was discussed — they can ask, and get a grounded answer based on actual records.

The doctor detail modal in the dashboard adds another practical layer: instead of reading raw notes like "disc met. interested. follow next wk", the rep sees "Dr. Sharma expressed interest in the product during the call and requested a follow-up meeting next week." That rewriting is done by the AI in one batch call, not one-by-one, keeping it fast.

---

## Running Locally

The backend requires Python 3.11+, PostgreSQL, and Redis. Copy `.env.example` to `.env` and fill in `DATABASE_URL`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `REDIS_URL`, and `JWT_SECRET`. Run `pip install -r requirements.txt`, apply the migration SQL files in order, then start the server with `uvicorn main:app --reload`.

The frontend requires Node 18+. From the `frontend/` directory, run `npm install` then `npm run dev`. It proxies API requests to `http://localhost:8000` by default.

For the async worker on Windows, start it separately: `python -m rq worker --worker-class rq.SimpleWorker`.

---

## Project Structure

```
app/
  api/routes.py          — all API endpoints
  ai/
    router.py            — keyword-based message router
    model_router.py      — dual-model dispatch with retry/fallback
    tools.py             — five LangChain @tool functions
    agent.py             — LangGraph create_react_agent setup
  core/
    auth.py              — JWT decode + get_current_user dependency
    rate_limit.py        — per-user request rate limiting
    redis_client.py      — cache, counters, resilience stats
  models/schemas.py      — Pydantic request/response models
  services/
    crm_service.py       — all database read/write operations
    ai_service.py        — chat() and format_notes_batch()
    queue_service.py     — RQ enqueue and metrics
    metrics_service.py   — system metrics aggregation
frontend/src/
  components/
    ChatAssistant.jsx    — main chat UI
    Dashboard.jsx        — metrics dashboard with doctor modal
    SystemPage.jsx       — infrastructure and AI metrics
    InteractionList.jsx  — recent interactions table
    LogForm.jsx          — structured interaction form
```
