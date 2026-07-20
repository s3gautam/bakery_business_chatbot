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

Save in database.

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

Store in DB

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

12AM-5AM

9AM-12PM

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

Database failure

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
