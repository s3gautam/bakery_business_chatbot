# WarmOven AI Ordering Assistant — Stage 1

Stage 1 of the WarmOven chatbot: menu Q&A, recommendations, and customer
feedback collection, in English, Hindi, and Hinglish (auto-detected). No
cart, checkout, or payment yet — order requests are routed to a phone
number. See `MASTER_PROMPT.md` for full product behavior and `CLAUDE.md`
for engineering standards and the full 3-stage roadmap.

## Stack

FastAPI + LangGraph agent + Groq (OpenAI-compatible) LLM + PostgreSQL +
Redis, containerized with Docker.

## Local setup

```bash
cp .env.example .env
# fill in GROQ_API_KEY at minimum

docker compose up --build
```

This starts Postgres, Redis, the API on `http://localhost:8000`, and the
Streamlit UI on `http://localhost:8501`, and runs `alembic upgrade head`
automatically.

### Without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# in a second terminal
streamlit run streamlit_app/Home.py
```

## UI

The Streamlit app (`streamlit_app/`) has two pages:

- **Home** — the customer-facing chat window.
- **⚙️ Configure** — an admin page to change, at runtime (no redeploy):
  - the menu source link (Swiggy or Zomato)
  - minimum cart value for free delivery
  - free delivery radius
  - delivery time
  - Swiggy/Zomato flat discount %
  - payment phone number and UPI ID
  - freeform extra instructions for the assistant

These settings live in the `business_config` table and are read by the
agent on every chat request — no restart needed after saving. Set
`API_BASE_URL` (default `http://localhost:8000`) if the UI and API run on
different hosts.

### Corporate SSL interception

If you're on a company laptop behind an SSL-inspecting proxy, see
`CLAUDE.md` → "Local Dev Environment: Corporate SSL Interception". Set
`REQUESTS_CA_BUNDLE` to your corporate CA bundle, or as a local-only
fallback set `DEV_DISABLE_SSL_VERIFY=true` in `.env`.

## Syncing the menu

The chatbot only ever reads menu data from the database — it never
scrapes live. Populate/refresh the menu with:

```bash
python -m scraper.swiggy_scraper
```

Rerun this any time the Swiggy menu changes.

## API

- `POST /chat` — send a customer message, get a reply
- `GET /menu` — list available menu items
- `POST /feedback` — submit feedback directly (bypassing chat)
- `GET /health` — liveness check

## Tests

```bash
pytest
```
