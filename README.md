# AI CRM Assistant

An intelligent CRM assistant built for pharmaceutical sales representatives. It enables reps to log doctor interactions, retrieve history, summarize notes, extract key entities, and receive context-aware next-step suggestions — all through a natural language chat interface powered by a large language model.

---

## Features

- **Log Interactions** — Record doctor visits and meetings with automatic name extraction, sentiment analysis, and follow-up suggestion
- **Edit Interactions** — Update notes on any existing interaction by ID
- **Summarize Notes** — Get a concise 1–2 sentence summary of logged interactions pulled directly from the database
- **Extract Entities** — Identify doctor name, product, location, and date from any text
- **Suggest Next Action** — Receive one specific, context-aware CRM action based on real logged history
- **Duplicate Detection** — Automatically detects near-identical entries (85% similarity threshold) and prompts before re-logging
- **New Entry Override** — Allows intentional re-logging via `new entry:` prefix
- **DB-Backed Responses** — All answers are grounded in real database records; no hallucinated names or details
- **Honest No-Entry Handling** — Returns a clear message when a queried doctor has no records in the CRM

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Database | PostgreSQL |
| DB Driver | psycopg2 |
| AI Framework | LangGraph + LangChain |
| LLM Provider | Groq |
| LLM Model | llama-3.1-8b-instant |
| Frontend | React 18 + Vite |
| Styling | Tailwind CSS |
| Environment | python-dotenv |
| Similarity Matching | difflib (SequenceMatcher) |

---

## AI & LangGraph Details

### LLM — Groq (llama-3.1-8b-instant)
Used for all natural language tasks: doctor name extraction, sentiment classification, note summarization, entity extraction, and next-step suggestion. Chosen for low-latency inference suitable for real-time chat.

### LangGraph — `@tool` + `create_react_agent`
All five tool functions are decorated with LangGraph's `@tool` decorator and registered in a `create_react_agent` graph. In the current architecture, routing is handled deterministically (see below) and tools are invoked directly — the agent graph is initialized and available but not used for live request dispatch.

### LangChain — `ChatGroq`, `SystemMessage`, `HumanMessage`
All LLM calls are made through LangChain's Groq integration with a strict system prompt applied globally to prevent hallucination, narrative drift, and uncertain phrasing.

### Five LangGraph Tools

| Tool | Function |
|---|---|
| `log_interaction` | Extracts doctor name + structured fields via LLM, writes to PostgreSQL, builds confirmation from parsed values |
| `edit_interaction` | Fetches doctor name from DB by ID, updates notes, returns deterministic confirmation — no LLM call |
| `summarize_text` | Fetches real notes from DB by doctor name, summarizes using LLM; returns "no entry" if doctor not found |
| `extract_entities` | Extracts doctor, product, location, date from text; appends DB history count if doctor is already logged |
| `suggest_next_action` | Pulls DB history for the named doctor (or most recent interaction) and suggests one specific next step |

### Deterministic Router
All requests are dispatched by a keyword-based Python router with zero LLM calls. This keeps latency low and routing fully predictable. Tools are called directly via `.invoke()` — no agent loop overhead.

### Duplicate Detection
Uses `difflib.SequenceMatcher` to compare incoming text against the 20 most recent interaction notes. If similarity is ≥ 85%, the entry is flagged as a duplicate and the user is prompted to confirm before re-logging.

---

## Workflow

```
User Message (Chat UI)
        │
        ▼
FastAPI  /chat  endpoint
        │
        ▼
Deterministic Router  (_route)
  ├── "update/edit" + ID  →  edit_interaction
  ├── "summarize/summary" →  summarize_text
  ├── "extract/identify"  →  extract_entities
  ├── "suggest/next step" →  suggest_next_action
  └── default             →  log_interaction
        │
        ▼
Tool Execution
  ├── DB lookup  (PostgreSQL via psycopg2)
  ├── LLM call   (Groq via LangChain)  [if needed]
  └── DB write   (INSERT / UPDATE)     [if needed]
        │
        ▼
Natural Language Response  →  Chat UI
```

---

## Conclusion

AI CRM Assistant demonstrates how large language models can be integrated into a real business workflow without sacrificing reliability or accuracy. By combining a strict system prompt, deterministic routing, database-grounded responses, and LangGraph tool registration, the system delivers consistent, hallucination-free output that a sales representative can trust in a live demo or production setting. The architecture keeps LLM calls minimal and purposeful — every response is backed by either real database records or explicitly provided text, never imagination.
