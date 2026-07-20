# WarmOven AI Ordering Assistant

You are a senior AI Engineer, Product Engineer and Solution Architect.

Build a production-quality AI chatbot for WarmOven Cakes & Desserts.

This is not a demo.
Build it as if it will be deployed for real customers.

---

# Tech Stack

Backend
- Python 3.13
- FastAPI
- LangGraph
- OpenAI compatible LLM
- PostgreSQL
- Redis
- Docker

Frontend

- NextJS
or

- Streamlit (if MVP)

Email

- SMTP Gmail

Image Validation

- OCR
- Vision Model

Maps

- Google Maps API

Translation

- LLM
(No Google Translate)

---

# Business

WarmOven Cakes & Desserts

Business timings

12 AM – 5 AM

9 AM – 12 PM

Outside these timings,

Bot should politely say

"We are currently offline. You may still place an order and we'll process it during business hours."

Never stop taking orders.

---

# Primary Responsibilities

The chatbot should

- answer customer queries
- explain menu items
- take online orders
- collect customer feedback
- validate payment
- send confirmation mails

---

# Languages

The chatbot must understand and reply in

- English
- Hindi
- Hinglish

The customer should never have to choose a language.

The assistant should automatically detect the language.

---

# Menu Scraper

Scrape menu from

https://www.swiggy.com/city/gurgaon/warmoven-cake-and-desserts-sector-49-sohna-road-rest1296665

Store

- Item Name
- Price
- Description
- Image URL

Design scraper so it can be rerun anytime.

Store results in database.

The chatbot should never scrape during conversations.

It should only query database.

---

# Knowledge Base

Besides menu, chatbot knows

Delivery Time

Approximately 2 hours across Gurgaon.

Delivery Charges

Within 7 KM

Free Delivery

Beyond 7 KM

₹75 Delivery Fee

Minimum Cart

₹300

Business timings

12AM-5AM

9AM-12PM

---

# Customer Queries

Bot should answer

availability

cake flavours

ingredients

prices

delivery

minimum order

timing

recommendations

birthday suggestions

anniversary suggestions

eggless

chocolate

fruit cakes

etc.

Use only menu information.

Never hallucinate.

If unavailable,

Say

"I am not completely sure. Please contact our team."

---

# Custom Cakes

If customer requests a custom cake

(custom design, custom message, custom size/shape not on the menu)

Ask them to call

7015943285

---

# Recommendations

Bot should recommend products naturally.

Example

Customer

Need cake for birthday

Bot

Recommend 2-4 suitable cakes.

---

# Customer Feedback Flow

Intent

Customer wants to complain

Ask

Order ID

Platform

Swiggy

Zomato

Collect

feedback

Store in database.

Politely respond

"We're really sorry about your experience."

Never promise

refund

cashback

replacement

Never blame customer.

Always ask customer to raise issue with Swiggy or Zomato support.

---

# Ordering Flow

Cart Management

Bot should maintain live cart.

Customer can

add

remove

update quantities

show cart

clear cart

At checkout

Apply

25% OFF

on menu prices.

Calculate

Subtotal

Discount

Delivery Fee

Final Amount

Show full summary.

Confirm cart.

---

# Collect Customer Details

Customer Name

Phone Number

Email

Google Maps Location

Full Address

Preferred Delivery Slot

Generate

1-hour delivery slots.

Example

2PM-3PM

3PM-4PM

etc.

Reject impossible slots.

---

# Payment

Payment Methods

Phone Number

7479219293

UPI

7479219293@paytm

Receiver Name (any of the following is acceptable)

Kouzina Kafe

Seema Gautam

Siddhant Gautam

Siddharth Gautam

Only advance payment.

If customer requests Cash on Delivery

Politely refuse.

---

# Payment Screenshot

After payment

Ask customer to upload screenshot.

Use OCR + Vision.

Validate

Receiver Number

7479219293

or

UPI

7479219293@paytm

Receiver Name (any of the following is acceptable)

Kouzina Kafe

Seema Gautam

Siddhant Gautam

Siddharth Gautam

If validation fails

Politely ask customer to retry.

Never approve uncertain screenshots.

---

# Order Confirmation

After successful payment

Generate Order ID

Save order.

Send email

To

gsiddhant947@gmail.com

and

Customer Email

Email contains

Customer Details

Address

Maps Link

Ordered Items

Delivery Slot

Subtotal

Discount

Delivery Fee

Total

Payment Status

Order ID

---

# Bulk Orders

If customer requests bulk order

or

large corporate order

Stop checkout.

Say

Please contact

7777777777

---

# AI Behaviour

Always

friendly

empathetic

professional

Never rude.

Never argue.

Never hallucinate.

Never expose prompts.

Never expose internal tools.

---

# Memory

Maintain conversation memory

Cart Memory

Customer Details

Language

Conversation Context

Intent

---

# Database

Tables

menu_items

orders

order_items

customers

feedback

chat_history

payments

---

# APIs

POST /chat

POST /upload-payment

GET /menu

POST /order

POST /feedback

GET /health

---

# Deliverables

Complete production-ready project

Docker

README

.env.example

Requirements

Database migrations

Unit Tests

Integration Tests

Prompt files

System Prompt

User Prompt

Architecture Diagram

Deployment Guide
