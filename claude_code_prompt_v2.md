# LeadForge — Claude Code Master Prompt

You are a senior full-stack engineer. Your job is to build **LeadForge** — a production-ready B2B SaaS platform for professional email discovery and verification — from scratch.

You have been given two reference documents:
- `PRD.md` — the full product requirements
- `architecture.md` — the complete technical architecture

Read both documents in full before writing a single line of code. Every decision in this build — folder structure, data models, service design, API shape, frontend layout — must match what is specified in those documents. If something is not specified, make a reasonable engineering decision and leave a one-line comment explaining it.

---

## YOUR MISSION

Build the complete MVP codebase. Not a scaffold. Not stubs. A real, working application where every file does what it says it does.

When you are finished, a developer should be able to run `docker-compose up`, open `http://localhost:3000`, sign up, and successfully discover and verify a professional email address.

---

## GROUND RULES

These apply to every file you write, no exceptions:

1. **No placeholders.** No `pass`, no `# TODO`, no `raise NotImplementedError`, no `return {}`. Every function must have a real implementation.

2. **Type everything.** Full type hints on all Python functions. Explicit TypeScript types on everything — no `any`.

3. **Async all the way.** All DB, Redis, HTTP, and SMTP calls must be async. No blocking I/O inside async functions.

4. **Errors are handled explicitly.** Every function that can fail has try/except with a meaningful response. No silent failures.

5. **No hardcoded secrets or URLs.** Everything comes from environment variables via the config system.

6. **DB sessions must close.** Use context managers or try/finally everywhere. No leaked connections.

7. **Consistent API responses.** Errors: `{detail: str, code: str}`. Success: matches Pydantic schema exactly.

8. **Log meaningful events.** Structured JSON logs. Log SMTP results, cache hits/misses, job state changes, request lifecycle. Never log raw passwords or full email addresses.

9. **UUIDs only.** No integer primary keys anywhere.

10. **Self-contained for MVP.** The app runs fully locally — no calls to third-party data APIs (Hunter, Apollo, etc.). DNS and SMTP connections are the only external dependencies.

---

## BUILD ORDER

Work through these phases in strict order. Do not start a phase until the previous one is complete and working.

### Phase 1 — Project Skeleton
Set up the monorepo structure, Docker Compose (all services: db, redis, api, worker, flower, frontend, nginx), `.env.example`, and the backend Dockerfile and `requirements.txt`. The architecture document specifies every service and the MVP hosting approach — follow it exactly.

### Phase 2 — Backend Core
Build `config.py`, `database.py`, `redis.py`, and `security.py`. These are the foundation everything else depends on. Get them right before moving on.

### Phase 3 — Data Layer
Build all SQLAlchemy models and Alembic migrations. The PRD data model section has every table, column, and constraint. Add all indexes specified in the architecture document. Run `alembic upgrade head` successfully before proceeding.

### Phase 4 — Schemas
Build all Pydantic v2 request/response schemas. Match the API endpoint specifications in the PRD exactly — field names, types, validation rules, and optionality.

### Phase 5 — Services
Build all backend services in this order:
1. Pattern generator (10 permutations, name normalization, ranking)
2. Verification pipeline stages: syntax → DNS/MX → disposable → catch-all → SMTP
3. Verification pipeline orchestrator (runs all stages, calculates confidence score)
4. Domain intelligence service (get/create/cache domain profiles)
5. Credit service (atomic check-and-deduct, refund, usage stats)
6. Storage service (local filesystem abstraction)

The confidence score formula is specified precisely in the PRD and architecture. Implement it exactly.

### Phase 6 — Scraper
Build the website contact scraper and Google Maps scraper using Playwright. Implement the proxy manager and user agent rotation. Follow the anti-bot guidance in the architecture document.

### Phase 7 — Workers
Build the Celery app config and both worker tasks: `process_bulk_job` and `process_maps_scrape`. Implement real progress tracking via Redis pub/sub. Implement webhook delivery on job completion.

### Phase 8 — API Routes
Build all FastAPI routes, dependencies, and middleware. Wire up auth (JWT + API key), rate limiting (sliding window via Redis), credit guards, and request logging. Every endpoint from the PRD must exist and work.

### Phase 9 — Frontend
Build the Next.js app in this order:
1. Types, API client, NextAuth config
2. Landing page
3. Auth pages (login, signup)
4. Dashboard layout with sidebar
5. Dashboard home (stats, quick search, recent history)
6. Search page (form + results with confidence bars + status badges)
7. Bulk search page (CSV upload, column mapper, job progress, download)
8. Lead scraper page (form + job progress + lead table)
9. Leads page (saved results, filter, export)
10. Settings page (account, API key management, billing stubs)

### Phase 10 — Data & Config
Create the disposable email domains data file (minimum 300 domains). Write the Nginx config. Finalize all environment variable defaults.

### Phase 11 — Tests
Write tests for the critical paths: pattern generator correctness, confidence score calculation, verification pipeline stages (mocked DNS/SMTP), API endpoint happy paths and error cases, credit deduction atomicity.

### Phase 12 — README
Write a complete README covering: what it is, prerequisites, local setup step by step, environment variable reference, running tests, API docs link, and deployment notes.

---

## DEFINITION OF DONE

The build is complete when all of the following are true:

- `docker-compose up` starts cleanly with no errors
- `http://localhost:3000` renders the LeadForge landing page
- A new user can sign up, log in, and reach the dashboard
- `POST /v1/discover` returns 10 ranked email permutations with confidence scores and verification statuses
- `POST /v1/verify` verifies a standalone email address
- CSV upload on the bulk page creates a Celery job visible in Flower at `http://localhost:5555`
- The Google Maps scraper form submits and shows job progress
- API key generation in Settings returns a key prefixed with `lf_`
- `GET /health` returns `{"status": "ok"}`
- All backend tests pass
- FastAPI auto-docs at `http://localhost:8000/docs` show every endpoint from the PRD

---

Start with Phase 1. Do not stop until you reach the definition of done.
