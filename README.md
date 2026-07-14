# AI-First CRM · HCP Interaction Log

An AI-first Customer Relationship Management screen for pharmaceutical field
representatives to log Healthcare Professional (HCP) interactions — built
with a LangGraph agent as the intelligent bridge between free-form natural
language and a structured, persisted CRM record.

Reps can log a visit **either** by typing directly into a structured form
**or** by describing the visit conversationally to an AI assistant — both
paths write to the exact same database record, so they can never drift out
of sync with each other.

---

## Tech Stack

| Layer      | Technology                                   |
|------------|-----------------------------------------------|
| Frontend   | React + Redux (Vite)                          |
| Backend    | Python, FastAPI                               |
| AI Agent   | LangGraph                                     |
| LLM        | Groq (`openai/gpt-oss-20b` — see note below)  |
| Database   | PostgreSQL (Neon)                             |
| Font       | Google Inter                                  |

### A note on the LLM model

The assignment specifies Groq's `gemma2-9b-it` model. During development,
Groq fully **decommissioned** this model — any request to it now returns
`model_decommissioned` (HTTP 400). Per Groq's own migration guidance, this
project uses `openai/gpt-oss-20b` instead, a currently supported Groq model
with strong tool-calling support (required here, since the agent relies
heavily on `bind_tools`). The model is configurable via the `GROQ_MODEL`
environment variable if a different model is preferred.

---

## Role of the LangGraph Agent

The LangGraph agent is the **sole actor** allowed to mutate the Interaction
record backing the structured form, when using the chat entry path. On
every chat turn:

1. The `agent` node reads the running conversation and, using the Groq LLM,
   decides whether the rep's message requires calling one or more of the
   5 tools below.
2. If so, LangGraph routes to the `tools` node, which performs the real
   database write and returns each tool's result as a `ToolMessage`.
3. The graph loops back to `agent`, so the LLM can see the tool results and
   either call another tool (e.g. `log_interaction` then
   `suggest_followups`) or produce a final natural-language reply.
4. Once the LLM responds with no further tool calls, the graph ends and the
   API layer reads the latest `Interaction` row back out of the database to
   refresh the form the user sees.

This keeps the chat UI and the structured form perfectly consistent: the
form only ever reflects what a tool actually persisted, never what the LLM
merely *said* it did.

The **direct form-edit path** (typing into the form itself) bypasses the
LLM entirely and writes through a dedicated `PATCH` endpoint straight to
the same `Interaction` row — deterministic, since no natural-language
extraction is needed for a field the rep is typing explicitly.

---

## The 5 LangGraph Tools

| # | Tool                     | Purpose                                                                 |
|---|--------------------------|--------------------------------------------------------------------------|
| 1 | `log_interaction` **(mandatory)** | Creates/populates the interaction record from a free-text description of a visit. Extracts every field it can find (HCP name, type, date, time, topics, materials, samples, sentiment, outcomes, follow-ups) and leaves anything unmentioned untouched. |
| 2 | `edit_interaction` **(mandatory)** | Modifies exactly one field of an already-logged interaction (e.g. "actually change the sentiment to neutral"), without touching anything else. |
| 3 | `search_or_create_hcp`   | Resolves the HCP name against the directory (fuzzy match). Creates a new HCP record if none exists, and links it to the current interaction. |
| 4 | `log_material_or_sample` | Incrementally adds materials shared or samples distributed, for follow-up mentions after the main interaction is already logged. |
| 5 | `suggest_followups`      | Generates 2–4 concrete next-step suggestions grounded in the logged topics/outcomes, populating the "AI Suggested Follow-ups" panel. |

---

## Architecture
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph.py       # LangGraph StateGraph, system prompt, LLM binding
│   │   │   ├── tools.py       # The 5 tools — real DB writes
│   │   │   └── state.py       # Agent state schema
│   │   ├── routers/
│   │   │   ├── chat.py        # POST /api/chat — invokes the agent
│   │   │   ├── interactions.py# GET current / PATCH fields / POST new
│   │   │   └── hcps.py        # HCP directory endpoints
│   │   ├── models.py          # SQLAlchemy models (HCP, Interaction, ChatMessage)
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── database.py        # Engine/session setup (Postgres, with pool_pre_ping)
│   │   └── main.py            # FastAPI app, CORS, router registration
│   ├── .env.example
│   └── requirements.txt
└── frontend/
└── src/
├── components/
│   ├── InteractionForm.jsx  # Structured form — directly editable
│   ├── ChatPanel.jsx        # Conversational entry path
│   └── Field.jsx            # Shared field wrapper + AI-update pulse
├── store/
│   ├── interactionSlice.js  # Form state, diffs AI-driven changes
│   └── chatSlice.js         # Chat message history, session id
├── api/
│   └── client.js            # fetch wrappers for all backend calls
└── App.jsx                  # Split layout: form + chat

---

## Setup & Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free [Groq API key](https://console.groq.com/keys)
- A free [Neon Postgres](https://neon.tech) database (or any Postgres/MySQL instance)

### 1. Clone the repo

```bash
git clone https://github.com/Vaishnavi-MS-36/hcp-crm.git
cd hcp-crm
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv

# macOS/Linux:
source .venv/bin/activate
# Windows (Git Bash):
source .venv/Scripts/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create a `.env` file in `backend/` (use `.env.example` as a template):

```dotenv
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
DATABASE_URL=postgresql+psycopg2://user:pass@your-neon-host/dbname?sslmode=require
CORS_ORIGINS=http://localhost:5173
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

The API will be live at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`. Tables are created automatically on startup
via `Base.metadata.create_all()` — no manual migration step needed.

### 3. Frontend setup

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The app will be live at `http://localhost:5173`.

---

## Using the App

- **Chat entry:** Describe a visit in plain English in the right-hand
  panel, e.g. *"Met Dr. Sharma today at 4pm, discussed OncoBoost efficacy
  data, she seemed positive and I left the Phase III brochure plus 10
  samples."* Watch the form populate live, with a teal pulse marking
  exactly which fields the AI just touched.
- **Form entry:** Type directly into any field on the left, click a
  sentiment option, or add a material/sample tag — changes save
  automatically and persist to Postgres.
- Both paths write to the same interaction record, so you can freely mix
  them — e.g. log the main visit via chat, then correct one field directly
  on the form, or vice versa.

---

## Design Decisions Worth Noting

- **Dual entry paths, single source of truth.** Rather than treating chat
  as the only way to fill the form, both the chat/agent path and a direct
  form-edit path write through to the same `Interaction` row via separate
  code paths (`agent/tools.py` for AI-driven writes, a dedicated `PATCH`
  route for manual writes), so the two can never drift apart.
- **The "AI updated" pulse is exclusively reserved for chat-driven
  changes** — manual form edits deliberately do not trigger it, so the
  causal link between "what I said in chat" and "what changed on screen"
  stays unambiguous.
- **Connection resilience.** Neon's free tier auto-suspends the compute
  after inactivity, which can leave the connection pool holding stale
  connections. `pool_pre_ping=True` and `pool_recycle=300` were added to
  `database.py` so the app transparently reconnects instead of erroring.

---

## Video Walkthrough

[Link to submission video]