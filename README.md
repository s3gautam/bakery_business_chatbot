# AI Ordering Assistant — Stage 1 + 2

Menu Q&A, recommendations, and customer feedback collection (Stage 1),
plus full in-chat ordering: cart, checkout, delivery slots, and payment
screenshot validation (Stage 2) — in English, Hindi, and Hinglish
(auto-detected). Order confirmation emails are Stage 3 (not built yet).
See `MASTER_PROMPT.md` for full product behavior and `CLAUDE.md` for
engineering standards and the full 3-stage roadmap.

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
# feedback emails (use a Gmail App Password, not your normal password).
# GROQ_VISION_MODEL is used for payment screenshot validation — verify
# it's a current Groq vision model ID before relying on it.

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
  - accepted receiver names on payment screenshots
  - freeform extra instructions for the assistant
- **🍰 Menu** — view the current menu and re-sync it from Swiggy/Zomato.

These settings live in `data/business_config.json`.

## Ordering (Stage 2)

Customers order directly in chat: "add 2 chocolate cakes" builds a cart,
"show cart" reviews it, "checkout" starts the flow (collects name/phone/
email/address, then a delivery slot, then shows payment instructions).
Payment is advance-only — the customer uploads a screenshot (a file
uploader appears once payment is due), which is validated in one call to
a vision-capable Groq model (no separate OCR library). On success, an
Order ID is generated and the order is confirmed; nothing is written to
a database — cart/customer/order state lives only in the browser's
`st.session_state` for that session.

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
