# WarmOven AI Ordering Assistant — Stage 1

Stage 1 of the WarmOven chatbot: menu Q&A, recommendations, and customer
feedback collection, in English, Hindi, and Hinglish (auto-detected). No
cart, checkout, or payment yet — order requests are routed to a phone
number. See `MASTER_PROMPT.md` for full product behavior and `CLAUDE.md`
for engineering standards and the full 3-stage roadmap.

## Stack

A single self-contained **Streamlit** app — no separate backend, no
database. The LangGraph agent runs in-process and calls **Groq**
(OpenAI-compatible) directly. Menu and business settings are read from
JSON files (`data/menu.json`, `data/business_config.json`); feedback is
emailed via Gmail SMTP instead of being stored anywhere. This keeps the
whole thing deployable for free on Streamlit Community Cloud alone.

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in GROQ_API_KEY at minimum; SMTP_USERNAME/SMTP_PASSWORD to enable
# feedback emails (use a Gmail App Password, not your normal password)

streamlit run streamlit_app/Home.py
```

Open `http://localhost:8501`.

### Corporate SSL interception

If you're on a company laptop behind an SSL-inspecting proxy, see
`CLAUDE.md` → "Local Dev Environment: Corporate SSL Interception". Set
`REQUESTS_CA_BUNDLE` to your corporate CA bundle, or as a local-only
fallback set `DEV_DISABLE_SSL_VERIFY=true` in `.env`.

## UI

- **Home** — the customer-facing chat window.
- **⚙️ Configure** — an admin page to change, at runtime (just a page
  reload, no redeploy):
  - the menu source link (Swiggy or Zomato)
  - minimum cart value for free delivery
  - free delivery radius
  - delivery time
  - Swiggy/Zomato flat discount %
  - payment phone number and UPI ID
  - freeform extra instructions for the assistant

These settings live in `data/business_config.json`.

## Syncing the menu

The chatbot only ever reads menu data from `data/menu.json` — it never
scrapes live. Populate/refresh it with:

```bash
python -m scraper.swiggy_scraper
```

Rerun this any time the Swiggy/Zomato menu changes.

## Deploying for free (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at `streamlit_app/Home.py`.
3. In the app's **Secrets**, set at minimum:
   ```toml
   GROQ_API_KEY = "your-groq-api-key"
   SMTP_USERNAME = "your-gmail-address@gmail.com"
   SMTP_PASSWORD = "your-gmail-app-password"
   ```
   (Streamlit injects secrets as environment variables, which
   `pydantic-settings` picks up the same way it reads `.env` locally.)
4. Deploy. `data/menu.json` and `data/business_config.json` ship with
   the repo as the initial menu/settings — edit them via the Configure
   page (writes persist for the life of the container) or by committing
   updated files.

Note: Streamlit Cloud's filesystem is ephemeral — Configure page edits
and menu syncs won't survive a redeploy/restart. For anything you want
to keep long-term, commit the updated `data/*.json` files back to the
repo.

## Tests

```bash
pytest
```
