# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

Bakery Business Chatbot — a conversational assistant for a bakery business.
Intended capabilities include handling customer inquiries (menu, pricing,
hours, orders), taking custom cake/order requests, and answering FAQs.

This repository is currently a fresh scaffold — no source code has been
added yet. As the project grows, update this file with:

- Tech stack (language, framework, LLM provider/SDK)
- Directory layout and where key logic lives
- How to install dependencies and run the app locally
- How to run tests and linters
- Environment variables / secrets required (never commit real values)
- Deployment notes, if any

## Development Conventions

- Prefer editing existing files over creating new ones.
- Keep changes scoped to what's requested; avoid speculative abstractions.
- No comments unless they explain non-obvious "why".
- See `MASTER_PROMPT.md` for the chatbot's persona, tone, and behavior rules.

## Commands

_To be filled in once the project is initialized (e.g. `npm install`,
`npm run dev`, `npm test`)._

## Architecture

There is no backend service and no database. It's a single self-contained
**Streamlit** app (`streamlit_app/`): the LangGraph agent
(`app/agent/graph.py`) runs in-process and calls Groq directly. This
keeps the whole thing deployable for free on Streamlit Community Cloud
alone. Do not reintroduce FastAPI, SQLAlchemy, Postgres, or Redis without
an explicit decision to do so — this was a deliberate simplification
(no order/feedback history needs to persist; feedback is emailed instead
of stored).

- Menu: `data/menu.json`, read/written via `app/store/menu_store.py`
  (`MenuStore`). The menu scraper (`scraper/swiggy_scraper.py`) writes
  here; the chatbot only ever reads from here, never scrapes live.
- Business settings: `data/business_config.json`, read/written via
  `app/store/config_store.py` (`ConfigStore`).
- Feedback and (later) order confirmations: emailed via
  `app/services/email_service.py` (`EmailService`, Gmail SMTP), never
  written to a database.
- Chat history: kept only in the Streamlit session (`st.session_state`)
  — not persisted across sessions/restarts.

## Configurable Business Settings

The following are **admin-configurable at runtime**, stored in
`data/business_config.json` (`app/store/models.py::BusinessConfig`),
never hardcoded:

- Menu source link (Swiggy or Zomato)
- Minimum cart value for free delivery
- Free delivery radius
- Delivery time
- Swiggy/Zomato flat discount %
- Payment phone number and UPI ID
- Freeform extra instructions appended to the assistant's system prompt

They're read/written via `ConfigStore` and edited through the Streamlit
**Configure** page (`streamlit_app/pages/1_⚙️_Configure.py`). The menu
scraper and the agent's system prompt both pull from this file — do not
reintroduce hardcoded copies of these values elsewhere.

The `order_phone_number`, `custom_cake_phone_number`, and
`bulk_order_phone_number` (call-to-order routing) remain env-var-backed
in `app/config.py` since they're not part of the Configure page's scope.

## Development Roadmap

Build this project in **3 incremental stages**. Do not jump ahead to a
later stage's scope until the current stage works end-to-end.

### Stage 1 — Menu & Feedback Bot (no ordering)

- Chatbot answers menu questions (items, prices, ingredients, flavours,
  recommendations, eggless/chocolate/fruit cakes, etc.) from `data/menu.json`
  only — never hallucinate.
- Chatbot collects customer feedback (Order ID, platform, feedback text)
  and emails it to the admin inbox — no refund/cashback/replacement
  promises, nothing stored in a database.
- Language auto-detection (English / Hindi / Hinglish).
- Business-hours-aware messaging.
- **No cart, no checkout, no payment.** If the customer wants to place an
  order, tell them to call **7015943285**.
- Custom cake requests: tell them to call **7015943285**.
- Bulk/corporate order requests: tell them to call **7777777777**.

### Stage 2 — Ordering + Payment Validation (implemented)

- Full cart management (`app/agent/tools/cart_tool.py`: add/remove/update/
  show/clear), checkout with configurable discount and delivery-fee logic
  (`compute_totals`), delivery slot selection (`app/services/
  delivery_slots.py`), and collection of customer details (name, phone,
  email, address, optional Maps link) — all driven by NLU-extracted
  intents in `app/agent/graph.py` (`cart_add`, `checkout`,
  `provide_customer_details`, `provide_delivery_slot`, etc.).
- The Payment tool (`app/agent/tools/payment_tool.py`) validates a
  customer-uploaded screenshot via a single vision-capable Groq call
  (combined OCR + understanding — see `LLMService.complete_with_image`,
  `GROQ_VISION_MODEL`), checking receiver number/UPI and receiver name
  against `BusinessConfig.accepted_receiver_names`. **The vision model
  name and its JSON-extraction behavior are unverified against a live
  Groq vision endpoint** (this was built and tested with a stubbed LLM,
  since this environment can't reach the Groq API) — if screenshot
  validation misbehaves in production, check `GROQ_VISION_MODEL` is a
  real, current Groq vision model ID first.
- On successful validation, the bot confirms the order to the customer
  (Order ID generated via `app/agent/tools/order_tool.py`) — but the
  confirmation email is **not** part of this stage yet. Nothing is
  written to a database; cart/customer/delivery/payment state lives only
  in `st.session_state` for the browser session (see
  `streamlit_app/Home.py`).
- Custom cake and bulk order routing (call the relevant number) still
  apply — this stage does not build custom-cake or bulk-order checkout.

### Stage 3 — Order Confirmation Emails

- Uses the Email tool (already built in `app/services/email_service.py`
  for Stage 1 feedback) to send order confirmation emails (with retry on
  failure) to:
  - the admin inbox (`gsiddhant947@gmail.com`)
  - the customer's email
- Email contains full order summary per `MASTER_PROMPT.md` (customer
  details, address, maps link, items, delivery slot, subtotal, discount,
  delivery fee, total, payment status, order ID).
- This is the stage where the full ordering flow described in
  `MASTER_PROMPT.md` becomes complete end-to-end.

## LLM Provider

- The LLM provider is **Groq** (OpenAI-compatible API).
- The Groq API key is supplied via the `GROQ_API_KEY` environment variable —
  never hardcode it, never commit it. Document it in `.env.example` as a
  placeholder only.
- Point the OpenAI-compatible client at Groq's base URL
  (`https://api.groq.com/openai/v1`) instead of OpenAI's.

## Local Dev Environment: Corporate SSL Interception

- Development happens on a company laptop that sits behind a corporate
  proxy performing SSL/TLS interception (MITM inspection). This means
  outbound HTTPS requests (Groq API, Google Maps API, SMTP, package
  installs, etc.) can fail certificate verification locally even though
  the requests are legitimate.
- When you hit SSL/TLS verification errors in **local development only**,
  it's acceptable to work around them by one of these methods, in order
  of preference:
  1. **Preferred**: point the HTTP client at the corporate root CA bundle
     (e.g. `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` env vars, or passing
     `verify=<path-to-corp-ca.pem>` to `httpx`/`requests` clients) if the
     CA cert is available on the machine.
  2. **Fallback**: if the CA bundle isn't available, disable certificate
     verification only for local development, gated behind an explicit
     environment flag (e.g. `DEV_DISABLE_SSL_VERIFY=true`), never as the
     default behavior.
- This SSL bypass must **never** apply in staging or production. Any code
  that disables verification must be conditional on an explicit local-dev
  flag, must log a visible warning when active, and must be excluded from
  production config/deployment (Docker/CI configs should not set the
  bypass flag).
- Do not silence SSL warnings globally (e.g. no blanket
  `urllib3.disable_warnings()` at import time) — scope any suppression to
  the specific dev-only client instantiation.

---

# Claude Development Instructions

You are the lead engineer on this project.

Think carefully before writing code.

Never generate placeholder implementations.

Every module must be production quality.

---

# Engineering Principles

- SOLID
- DRY
- Clean Architecture
- Repository Pattern
- Dependency Injection
- Type Safety
- Async wherever useful

---

# AI Principles

The chatbot is an AI Agent.

Never hardcode conversations.

Use intent detection.

Maintain structured memory.

Support

- Hindi
- English
- Hinglish

Automatically detect language.

---

# Tool Calling

The agent must have tools.

## Menu Tool

Search menu database.

Never hallucinate.

---

## Cart Tool

Add item

Remove item

Update quantity

Clear cart

Compute totals

Apply discounts

---

## Recommendation Tool

Recommend cakes.

Birthday

Anniversary

Kids

Chocolate

Eggless

Premium

Budget

---

## Feedback Tool

Collect

Order ID

Platform

Feedback

Email to admin inbox (no database).

---

## Payment Tool

Validate screenshot.

OCR

Vision

Receiver Name

Receiver Number

UPI

Only accept confirmed payments.

---

## Email Tool

Send confirmation email.

Send to admin.

Send to customer.

Retry on failures.

---

## Order Tool

Create Order

Generate Order ID

Email order details (no database)

---

# Agent State

Conversation State

Current Intent

Detected Language

Cart

Customer Details

Payment Status

Delivery Slot

---

# Memory

Short Term

Conversation

Long Term

Customer

Order History

---

# Prompting

Always answer from menu.

Never invent menu items.

Never invent prices.

Never invent availability.

---

# Business Rules

Business Hours

Closed 5AM-9AM

Open the rest of the day (9AM-5AM next day)

Delivery

Approx 2 Hours

Delivery

Free within 7KM

₹75 after 7KM

Minimum Order

₹300

Discount

25%

Bulk Orders

7777777777

Payment

Advance Only

Receiver

Kouzina Kafe

---

# Safety

Never promise refunds.

Never promise cashback.

Never promise compensation.

Never claim order has been placed until payment validation succeeds.

---

# Error Handling

Gracefully recover from

OCR failures

Email failures

Payment mismatch

File storage read/write failure

LLM timeout

Network timeout

---

# Logging

Log

Intent

Orders

Errors

Payments

Emails

Feedback

Tool Calls

Never log secrets.

---

# Testing

Create automated tests for

Cart

Discount

Language detection

Order flow

Feedback flow

Payment validation

Email sending

Business hours

Delivery fee

Minimum cart validation

Bulk order routing

---

# Code Quality

Every function

typed

documented

tested

No TODOs

No placeholder code

No duplicated logic

No dead code

Production quality only.
