# CLAUDE.md — Mart AI

Multi-tenant grocery ordering SaaS: an AI shopping agent for customers, plus a
merchant operations dashboard for each mart.

## The one principle that governs everything

**AI is the interface. PostgreSQL + FastAPI are the source of truth.**

The LLM never reads or writes SQL, never computes a price, never decides stock
availability, and never produces a number that reaches a customer or a report.
It calls typed tools; those tools call services; services own the business
rules. If a number appears in a dashboard or an invoice, a SQL query produced
it.

## Hard requirements

- **Multi-tenant.** One deployment serves many independent marts. Every
  tenant-owned row carries `tenant_id`, and every query is scoped by it.
  Cross-tenant data leakage is the single worst bug this codebase can have.
- **Both clients ship.** A **web app** (Next.js — merchant dashboard *and*
  customer ordering client) and a **mobile app** (Expo/React Native, Play
  Store). Both consume the identical API. No endpoint may be web-only or
  mobile-only.
- **Order status and payment status are separate columns.** `READY_FOR_PICKUP +
  UNPAID` means pay-at-store; `READY_FOR_PICKUP + PAID` means prepaid. Never
  collapse these into one field.
- **Professional UI.** The merchant dashboard follows Square Dashboard /
  Shopify Admin / DoorDash Merchant Portal conventions. The customer chat
  follows Instacart conventions.

## Stack

### Backend (`backend/`)
| Component | Choice |
|---|---|
| Interpreter | Python **3.12** (`.venv/`) — 3.14 is too new for parts of the async-DB/AI wheel ecosystem |
| API | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x **async** + asyncpg |
| Migrations | Alembic |
| Database | PostgreSQL 16 (local, `mart_ai` / `mart_ai_test`) |
| Schemas/config | Pydantic v2 + pydantic-settings |
| Auth | `python-jose` JWTs carrying `tenant_id`; **`bcrypt` used directly** |
| Cache | Redis — pickup-code attempt limits, rate limiting |

### AI (`backend/app/agents/`)
| Component | Choice |
|---|---|
| Orchestration | LangGraph, with `AsyncPostgresSaver` checkpoints in the same Postgres |
| Planning | `deepagents` — added only when multi-item planning needs it, not upfront |
| Provider | **Pluggable.** `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_MODEL` env vars |

Grok (xAI), Groq and OpenAI all speak the OpenAI wire format, so one adapter
covers all three; Gemini gets a second adapter. Switching providers is an env
change, never a code change.

### Web (`web/`) — Next.js 15 App Router, TypeScript, Tailwind v4, shadcn/ui, TanStack Query, Recharts
### Mobile (`mobile/`) — Expo, TypeScript, NativeWind

## Why `bcrypt` and not `passlib`

`passlib` 1.7.4 (last released 2020) crashes against `bcrypt>=5` inside its own
backend detection. We call `bcrypt` directly and **SHA-256 pre-hash** passwords
to base64 before hashing, the way Django's `BCryptSHA256PasswordHasher` does,
so bcrypt's 72-byte input limit cannot silently truncate a long password.

## Layering — do not skip a layer

```
api/v1/endpoints/   HTTP only: parse, authorize, delegate, serialize
services/           business rules, state-machine transitions, orchestration
repositories/       data access, ALWAYS tenant-scoped
models/             SQLAlchemy ORM
```

An endpoint never touches a repository directly. A repository never contains
business rules. An agent tool calls a **service**, never a repository.

## Order state machine

```
DRAFT → PENDING_CONFIRMATION → CONFIRMED → PACKING → READY_FOR_PICKUP → COLLECTED
```

Cancellation is an explicit transition, legal only from `CONFIRMED` and
`PACKING`. Transitions are validated in the service layer — never by assigning
a status string from an endpoint.

Payment status is independent: `UNPAID → PAYMENT_PENDING → PAID → REFUNDED`.

## Commands

```bash
source .venv/bin/activate              # from repo root

cd backend
uvicorn app.main:app --reload          # dev server, :8000
pytest                                 # full suite
pytest tests/unit -q                   # fast unit tests
alembic revision --autogenerate -m ""  # new migration
alembic upgrade head                   # apply migrations
ruff check . && ruff format .          # lint + format
mypy app                               # type check
```

## Conventions

- **Async all the way down.** Endpoint → service → repository → SQLAlchemy. No
  sync DB calls in the request path.
- **TDD.** Write the failing test first. Tests run against a real
  `mart_ai_test` Postgres database, never SQLite — we depend on PG semantics.
- **Money is `Numeric(12, 2)`**, never `float`. Quantities that can be
  fractional (1.5 kg) are `Numeric`, not `int`.
- **Timestamps are `timezone=True` UTC.** Format for display at the client.
- Secrets live in `backend/.env`, which is never committed. `.env.example`
  documents every variable.

## Build phases

1. **Multi-tenant core** — auth, tenants, merchant/staff/customer users, products, categories, inventory
2. **Ordering** — customer web client, text AI agent, product search, cart, order creation
3. **Merchant operations** — dashboard, live order board, PACKING → READY → pickup code → COLLECTED
4. **Voice** — STT/TTS for Urdu, Roman Urdu, English
5. **Payments** — prepaid vs pay-at-store, payment state transitions
6. **Analytics** — sales, revenue, low-stock alerts, AI analytics queries
7. **Mobile app** — Expo client, QR deep-linking, Play Store build
