# LeadForge — Technical Architecture
**Version:** 1.0  
**Status:** Ready for Engineering  
**Last Updated:** March 2026

---

## Table of Contents

1. System Overview
2. High-Level Architecture Diagram
3. Tech Stack
4. Frontend Architecture
5. Backend Architecture
6. Email Pattern Generator
7. Email Validation Engine
8. Lead Scraping Pipeline
9. Queue System
10. Database Schema & Access Patterns
11. API Layer
12. Worker Services
13. Rate Limiting Strategy
14. Anti-Bot Considerations
15. Caching Strategy
16. Logging & Monitoring
17. Security Considerations
18. Hosting Architecture
19. Scaling to Millions of Searches

---

## 1. System Overview

LeadForge is a multi-service SaaS platform built around three core workflows:

1. **Email Discovery** — Generate candidate email permutations from name + domain, rank by pattern prevalence, verify via SMTP.
2. **Email Verification** — Run a known email through syntax, DNS, disposable, catch-all, and SMTP checks.
3. **Lead Scraping** — Extract business contacts from Google Maps and websites, then pipe into Email Discovery automatically.

The system is designed to be **cheap to run at MVP** (can operate on a single $50/mo VPS + managed Postgres) and **horizontally scalable** (Kubernetes-ready worker pools) as volume grows.

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENTS                                      │
│   Next.js App (Browser)    │    REST API Consumers (n8n, Zapier)     │
└──────────────┬─────────────┴────────────────┬────────────────────────┘
               │ HTTPS                         │ HTTPS + API Key
               ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY / NGINX                            │
│   Rate limiting │ TLS termination │ Auth middleware │ Request logging │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
               ┌───────────────▼───────────────┐
               │      FASTAPI APPLICATION        │
               │  (Python — stateless, 2+ pods) │
               └───────┬───────────┬────────────┘
                       │           │
           ┌───────────▼──┐  ┌─────▼──────────────┐
           │  POSTGRES DB  │  │   REDIS CACHE/QUEUE │
           │  (Primary +   │  │  (BullMQ jobs,      │
           │   Read Replica)│  │   domain cache,     │
           │               │  │   rate limit state) │
           └───────────────┘  └────────┬────────────┘
                                       │ Job dispatch
                    ┌──────────────────┼──────────────────┐
                    │                  │                   │
          ┌─────────▼──────┐  ┌────────▼──────┐  ┌───────▼────────┐
          │  SMTP VERIFIER  │  │  SCRAPER POOL │  │  DNS RESOLVER  │
          │  WORKERS        │  │  WORKERS      │  │  WORKERS       │
          │  (Python pods)  │  │  (Playwright) │  │  (Python pods) │
          │  Rotating IPs   │  │  Rotating IPs │  │                │
          └─────────────────┘  └───────────────┘  └────────────────┘
                    │                  │
          ┌─────────▼──────┐  ┌────────▼──────────┐
          │  SMTP PROXY     │  │  SCRAPING PROXY    │
          │  (Rotating IP   │  │  (Residential      │
          │   pool via      │  │   proxy rotation)  │
          │   ProxyMesh /   │  └────────────────────┘
          │   self-managed) │
          └─────────────────┘
```

---

## 3. Tech Stack

### Frontend
| Layer | Technology | Rationale |
|---|---|---|
| Framework | Next.js 14 (App Router) | SSR for landing pages, React for app UI |
| Styling | Tailwind CSS + shadcn/ui | Fast, consistent component library |
| State management | Zustand | Lightweight; no Redux overhead |
| Data fetching | TanStack Query | Caching, pagination, background refetch |
| Tables | TanStack Table | Handles large result sets efficiently |
| Auth | NextAuth.js | Easy OAuth + credentials; JWT sessions |
| Hosting | Vercel | Zero-config CI/CD, edge CDN |

### Backend
| Layer | Technology | Rationale |
|---|---|---|
| Framework | FastAPI (Python 3.12) | Async-native, auto-docs, fast |
| Auth | JWT (RS256) + API keys | Stateless; API keys stored as bcrypt hashes |
| Validation | Pydantic v2 | Request/response validation |
| ORM | SQLAlchemy 2.0 (async) | Type-safe, works with asyncpg |
| Task queue | Celery + Redis | Mature, well-documented, battle-tested |
| SMTP library | aiosmtplib | Async SMTP for non-blocking verification |
| DNS library | dnspython | MX record lookup |
| Scraping | Playwright (Python) | Full JS rendering for Google Maps |
| HTTP client | httpx (async) | For website scraping |
| Proxy rotation | ProxyMesh or rotating-proxy pool | IP rotation for SMTP and scraping |

### Database & Storage
| Layer | Technology | Notes |
|---|---|---|
| Primary DB | PostgreSQL 16 | Managed via Supabase or AWS RDS |
| Cache | Redis 7 | ElastiCache or self-hosted via Docker |
| Job queue | Redis (via Celery broker) | Same Redis instance on MVP |
| File storage | AWS S3 (or Cloudflare R2) | CSV uploads and results downloads |
| Search index | PostgreSQL full-text (MVP) | Upgrade to Elasticsearch post-MVP if needed |

### Infrastructure
| Layer | Technology | Notes |
|---|---|---|
| Containers | Docker | All services containerized |
| Orchestration | Docker Compose (MVP) → K8s (scale) | Start simple |
| CI/CD | GitHub Actions | Build → test → deploy pipeline |
| Hosting | AWS (or Hetzner for cost) | See Section 18 |
| Monitoring | Grafana + Prometheus | Self-hosted or Grafana Cloud free tier |
| Logging | Loki + Grafana | Structured JSON logs |
| Alerts | PagerDuty or Grafana alerting | |
| Error tracking | Sentry | Frontend and backend |
| Secret management | AWS Secrets Manager or Doppler | Never hardcode keys |

---

## 4. Frontend Architecture

```
/app
  /layout.tsx              — root layout, auth session provider
  /(auth)
    /login/page.tsx
    /signup/page.tsx
  /(dashboard)
    /page.tsx              — dashboard home (usage stats, quick search)
    /search/page.tsx       — single email lookup
    /bulk/page.tsx         — CSV upload + job tracker
    /scraper/page.tsx      — Google Maps scraper UI
    /leads/page.tsx        — saved lead lists
    /settings/page.tsx     — API keys, billing, account
  /api                     — Next.js API routes (thin proxy to FastAPI)
    /auth/[...nextauth].ts
    /proxy/[...path].ts    — forward authenticated requests to FastAPI

/components
  /ui                      — shadcn base components
  /search                  — SearchForm, ResultsTable, ConfidenceBar
  /bulk                    — ColumnMapper, JobProgress, ResultsDownload
  /scraper                 — ScraperForm, LeadTable
  /shared                  — CreditBadge, StatusBadge, EmptyState

/lib
  /api.ts                  — typed API client (wraps fetch + auth headers)
  /hooks                   — useSearch, useBulkJob, useCredits
  /utils                   — formatConfidence, statusColor, csvParser
```

**Key frontend decisions:**

- The Next.js `/api/proxy` route forwards all API requests to FastAPI, so the API key and JWT are never exposed to the browser's network tab.
- WebSocket connection via native browser WebSocket to poll job progress; fall back to polling every 3s if WS unavailable.
- CSV column mapper is a drag-drop UI built in React DnD Kit — maps CSV headers to expected fields without requiring users to reformat their spreadsheets.
- Confidence score displayed as a color-coded progress bar: green ≥80, yellow 50–79, red <50.

---

## 5. Backend Architecture

### Project Structure
```
/leadforge-api
  /app
    /core
      config.py            — settings from env vars via Pydantic BaseSettings
      security.py          — JWT creation/validation, API key hashing
      database.py          — async SQLAlchemy engine + session factory
      redis.py             — Redis connection pool
    /api
      /v1
        /routes
          discover.py      — POST /v1/discover
          verify.py        — POST /v1/verify
          bulk.py          — POST /v1/bulk, GET /v1/jobs/{id}
          scrape.py        — POST /v1/scrape/maps
          account.py       — GET /v1/account
        dependencies.py    — auth, rate limit, credit check deps
    /services
      pattern_generator.py — email permutation logic
      verification/
        syntax_checker.py
        dns_resolver.py
        disposable_checker.py
        catchall_detector.py
        smtp_verifier.py
        pipeline.py        — orchestrates all stages
      scraper/
        maps_scraper.py
        website_scraper.py
        proxy_manager.py
      domain_intelligence.py
      credit_service.py
    /workers
      celery_app.py        — Celery app init
      tasks/
        bulk_discovery.py
        bulk_verification.py
        maps_scrape.py
    /models
      user.py
      search.py
      email_result.py
      domain_profile.py
      bulk_job.py
      scraped_lead.py
    /schemas
      discover.py          — Pydantic request/response schemas
      verify.py
      bulk.py
      scrape.py
  /migrations              — Alembic migrations
  /tests
  docker-compose.yml
  Dockerfile
```

### Request Lifecycle (Single Discovery)

```
POST /v1/discover
     │
     ▼
[Auth middleware] — validate JWT or API key; attach user to request
     │
     ▼
[Rate limit middleware] — check Redis for request count this minute
     │
     ▼
[Credit check] — verify user has ≥1 credit; reserve credit optimistically
     │
     ▼
[Pattern Generator] — generate 10 permutations from name + domain
     │
     ▼
[Domain Intelligence] — check Redis/Postgres for cached domain profile
     │ (cache miss → async DNS + catch-all check, update cache)
     ▼
[Verification Pipeline] — run all 5 stages on top 3–5 candidates
     │
     ▼
[Score Calculator] — compute confidence per permutation
     │
     ▼
[Persist to DB] — write search + email_results rows
     │
     ▼
[Deduct credit] — finalize credit transaction
     │
     ▼
[Return response] — ranked JSON results
```

---

## 6. Email Pattern Generator

```python
# services/pattern_generator.py

PATTERNS = [
    "{f}.{l}",          # john.smith
    "{f}{l}",           # johnsmith
    "{f}",              # john
    "{fi}{l}",          # jsmith
    "{f}{li}",          # johns
    "{fi}.{l}",         # j.smith
    "{f}_{l}",          # john_smith
    "{l}.{f}",          # smith.john
    "{l}",              # smith
    "{l}{fi}",          # smithj
]

def generate_permutations(first: str, last: str, domain: str) -> list[str]:
    f = normalize(first)       # lowercase, ASCII, strip special chars
    l = normalize(last)
    fi = f[0]                  # first initial
    li = l[0]                  # last initial

    candidates = []
    for pattern in PATTERNS:
        local = pattern.format(f=f, l=l, fi=fi, li=li)
        candidates.append(f"{local}@{domain}")

    return candidates

def normalize(name: str) -> str:
    """Convert to lowercase ASCII, remove non-alpha characters."""
    import unicodedata
    name = unicodedata.normalize('NFD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z]', '', name.lower())
```

**Pattern ranking enhancement:**

When `domain_profile.predominant_pattern` is set, reorder the output list so the matching pattern appears first. All others retain original order. This ensures the most likely email surfaces at position 0 in the results.

```python
def rank_by_domain_profile(candidates, domain_profile):
    if not domain_profile or not domain_profile.predominant_pattern:
        return candidates
    
    primary_pattern = domain_profile.predominant_pattern
    primary = [c for c in candidates if c.pattern == primary_pattern]
    rest = [c for c in candidates if c.pattern != primary_pattern]
    return primary + rest
```

---

## 7. Email Validation Engine

### Stage 1 — Syntax Validation
```python
import re

RFC_5321_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
)

def validate_syntax(email: str) -> bool:
    return bool(RFC_5321_REGEX.match(email))
```

### Stage 2 — MX Record Check
```python
import dns.resolver

async def check_mx(domain: str) -> list[str] | None:
    """Returns list of MX hostnames or None if no MX found."""
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return sorted(
            [str(r.exchange).rstrip('.') for r in answers],
            key=lambda x: answers.rrset.ttl  # sort by preference
        )
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return None
```

Cache MX results in Redis with TTL of 86,400 seconds (24 hours):
```
Key:   mx:{domain}
Value: JSON array of MX hostnames
TTL:   86400
```

### Stage 3 — Disposable Email Detection
```python
# Load blocklist once at startup into a Python set (fast O(1) lookup)
# Source: https://github.com/disposable-email-domains/disposable-email-domains

DISPOSABLE_DOMAINS: set[str] = set()

def load_disposable_list():
    global DISPOSABLE_DOMAINS
    with open("data/disposable_domains.txt") as f:
        DISPOSABLE_DOMAINS = {line.strip().lower() for line in f if line.strip()}

def is_disposable(domain: str) -> bool:
    return domain.lower() in DISPOSABLE_DOMAINS
```

Update blocklist weekly via cron job that pulls latest from GitHub.

### Stage 4 — Catch-All Detection
```python
import aiosmtplib
import random
import string

async def is_catch_all(domain: str, mx_host: str) -> bool:
    """Send SMTP probe to a random address. If accepted, domain is catch-all."""
    random_local = ''.join(random.choices(string.ascii_lowercase, k=16))
    probe_address = f"{random_local}@{domain}"
    
    try:
        result = await smtp_probe(probe_address, mx_host)
        return result.code == 250
    except Exception:
        return False  # If probe fails, assume not catch-all (safe default)
```

Cache catch-all result in Redis with TTL of 43,200 seconds (12 hours):
```
Key:   catchall:{domain}
Value: "true" | "false"
TTL:   43200
```

**Special case:** Known large providers (gmail.com, outlook.com, yahoo.com, googlemail.com, hotmail.com) are always flagged as catch-all without probing — they accept all RCPT TO at the gateway level.

### Stage 5 — SMTP Handshake
```python
import aiosmtplib

SENDER_DOMAIN = "verify.leadforge.io"   # warmed-up sending domain
SENDER_EMAIL  = f"check@{SENDER_DOMAIN}"

async def smtp_verify(email: str, mx_host: str) -> SMTPResult:
    try:
        smtp = aiosmtplib.SMTP(
            hostname=mx_host,
            port=25,
            timeout=10,
            source_address=get_next_ip()  # pull from rotating IP pool
        )
        
        await smtp.connect()
        await smtp.ehlo(SENDER_DOMAIN)
        await smtp.mail(SENDER_EMAIL)
        
        code, message = await smtp.rcpt(email)
        await smtp.quit()
        
        return SMTPResult(code=code, message=message)
        
    except aiosmtplib.SMTPConnectError:
        # Port 25 blocked — try 587
        return await smtp_verify_587(email, mx_host)
    except asyncio.TimeoutError:
        return SMTPResult(code=0, status="timeout")
    except Exception as e:
        return SMTPResult(code=0, status="error", detail=str(e))
```

**SMTP Response Code Mapping:**

| Code | Interpretation | Status |
|---|---|---|
| 250 | Mailbox exists | `verified` |
| 251 | User not local but forwarded | `verified` |
| 550 | Mailbox not found | `invalid` |
| 551 | User not local, no forward | `invalid` |
| 552/553 | Mailbox unavailable | `invalid` |
| 421 | Service temporarily unavailable | `retry` |
| 450/451 | Mailbox busy / temp fail | `retry` |
| 452 | Mailbox full | `possibly_valid` |
| 0 | Connection failed / timeout | `unknown` |

**Retry logic:** On `retry` codes, wait 15 seconds and attempt once more. If still failing, return `unknown`.

### Confidence Score Calculator
```python
def calculate_confidence(
    pattern_rank: int,            # 0 = most popular pattern for domain
    domain_pattern_known: bool,
    domain_pattern_confidence: float,
    smtp_status: str,
    is_catch_all: bool,
    is_disposable: bool
) -> int:
    
    if is_disposable:
        return 0
    
    # Base: pattern popularity (top pattern = 40, decreasing)
    base = max(40 - (pattern_rank * 5), 5)
    
    # Domain pattern boost
    if domain_pattern_known and pattern_rank == 0:
        base += int(domain_pattern_confidence * 30)
    
    # SMTP result
    if smtp_status == "verified":
        base += 30
    elif smtp_status == "invalid":
        base = max(base - 60, 0)
    elif smtp_status == "possibly_valid":
        base += 10
    # unknown / timeout: no adjustment
    
    # Catch-all penalty
    if is_catch_all:
        base = max(base - 20, 0)
    
    return min(base, 100)
```

---

## 8. Lead Scraping Pipeline

### Google Maps Scraper

```
Input: query="HVAC companies", location="Austin, TX"
       ↓
Playwright opens headless Chromium
       ↓
Navigate to: https://www.google.com/maps/search/{query}+{location}
       ↓
Scroll results panel to load all listings (up to max_results)
       ↓
For each listing:
  - Extract: business_name, address, phone, website_url, rating
       ↓
For each website_url:
  - httpx GET with 10s timeout
  - Extract emails from HTML (regex: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})
  - Extract contact page links (/contact, /about, /team, /staff)
  - Fetch contact pages and repeat extraction
       ↓
Deduplicate extracted emails by domain
       ↓
If no email found: queue for Email Discovery using business owner name heuristics
       ↓
Store results → scraped_leads table
       ↓
If auto_discover_emails=true: enqueue discovery job for each lead without a direct email
```

**Anti-detection measures for scraper:**
- Random viewport size (1280–1920 x 800–1080)
- Random user agent from pool of 20 real browser UAs
- Human-like scroll timing (random delays 800ms–2400ms between actions)
- Residential proxy rotation (1 IP per domain, max 5 requests before rotate)
- Random mouse movement via Playwright's mouse API before clicks

### Website Contact Scraper

```python
async def scrape_website_emails(url: str) -> list[str]:
    EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
    
    emails = set()
    pages_to_check = [url]
    checked = set()
    
    # Also check common contact paths
    from urllib.parse import urljoin
    contact_paths = ['/contact', '/contact-us', '/about', '/team', '/staff', '/people']
    for path in contact_paths:
        pages_to_check.append(urljoin(url, path))
    
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for page_url in pages_to_check[:6]:  # max 6 pages per domain
            if page_url in checked:
                continue
            checked.add(page_url)
            
            try:
                resp = await client.get(page_url, headers={"User-Agent": get_random_ua()})
                if resp.status_code == 200:
                    found = EMAIL_REGEX.findall(resp.text)
                    emails.update(found)
            except Exception:
                continue
    
    # Filter out obvious non-personal emails
    filtered = [e for e in emails if not any(
        prefix in e.split('@')[0] for prefix in 
        ['info', 'hello', 'support', 'contact', 'admin', 'noreply', 'no-reply', 'sales', 'help']
    )]
    
    return filtered
```

---

## 9. Queue System

### Celery Configuration

```python
# workers/celery_app.py
from celery import Celery

celery_app = Celery(
    "leadforge",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
    include=["workers.tasks.bulk_discovery", "workers.tasks.maps_scrape"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,           # Only ack after task completes (no lost jobs)
    worker_prefetch_multiplier=1,  # One task at a time per worker (SMTP is slow)
    task_routes={
        "tasks.smtp_verify": {"queue": "smtp"},
        "tasks.scrape_maps": {"queue": "scrape"},
        "tasks.bulk_discovery": {"queue": "bulk"},
    },
    task_time_limit=300,           # 5 min hard limit per task
    task_soft_time_limit=240,      # 4 min soft limit (raises exception)
)
```

### Queue Structure

| Queue | Workers | Task Types | Priority |
|---|---|---|---|
| `smtp` | 4–20 (scale with load) | Individual SMTP verifications | High |
| `bulk` | 2–8 | Bulk job orchestration | Medium |
| `scrape` | 2–4 | Google Maps + website scraping | Low |
| `default` | 2 | Misc async tasks | Low |

### Bulk Job Processing
```
POST /v1/bulk (1000 contacts)
     │
     ▼
Create bulk_job record (status: queued)
     │
     ▼
Celery task: process_bulk_job(job_id)
     │
     ├─ Split into batches of 50 contacts
     │
     ├─ For each batch:
     │    ├─ Dispatch 50 chord tasks (parallel SMTP verification)
     │    ├─ Chord callback: save results, update job progress
     │    └─ Update bulk_job.completed += 50
     │
     ├─ After all batches complete:
     │    ├─ Generate CSV result file → upload to S3
     │    ├─ Update bulk_job.status = "completed"
     │    ├─ Update bulk_job.output_file_url
     │    └─ Fire webhook if webhook_url set
     │
     └─ Notify user via in-app notification
```

**Progress tracking:** Each batch completion emits a Redis pub/sub event on channel `job:{job_id}:progress`. The FastAPI `/v1/jobs/{id}` endpoint subscribes and streams progress via Server-Sent Events (SSE) or returns current state on poll.

---

## 10. Database Schema & Access Patterns

### Indexes (Critical for Performance)

```sql
-- Fast lookup by user for dashboard
CREATE INDEX idx_searches_user_id ON searches(user_id, created_at DESC);

-- Fast domain profile lookups (high frequency)
-- domain_profiles.domain is PRIMARY KEY — no additional index needed

-- Fast job status polling
CREATE INDEX idx_bulk_jobs_user_status ON bulk_jobs(user_id, status, created_at DESC);

-- Email deduplication check
CREATE INDEX idx_email_results_email ON email_results(email);
CREATE INDEX idx_email_results_search ON email_results(search_id);

-- Credit balance queries
CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id, created_at DESC);
```

### Key Access Patterns

| Operation | Query | Frequency |
|---|---|---|
| Get domain profile | `SELECT * FROM domain_profiles WHERE domain = $1` | Very High |
| Check recent search for same name+domain | `SELECT * FROM searches WHERE user_id=$1 AND domain=$2 AND first_name=$3 AND last_name=$4 AND created_at > NOW()-INTERVAL '24h'` | High |
| Save search result | INSERT into searches + email_results | High |
| Get user credits | `SELECT credits FROM users WHERE id=$1` | Very High |
| Deduct credits (atomic) | `UPDATE users SET credits = credits - $1 WHERE id=$2 AND credits >= $1 RETURNING credits` | High |
| Poll job status | `SELECT status, completed, total FROM bulk_jobs WHERE id=$1` | Medium |

### Result Caching

Before running discovery, check if same name+domain was searched within 24 hours by any user. Return cached results (no SMTP re-verification, no credit charge).

```sql
SELECT s.id, er.*
FROM searches s
JOIN email_results er ON er.search_id = s.id
WHERE s.domain = $1
  AND s.first_name = $2
  AND s.last_name = $3
  AND s.created_at > NOW() - INTERVAL '24 hours'
ORDER BY er.confidence DESC
LIMIT 10;
```

---

## 11. API Layer

### Middleware Stack (FastAPI)

```python
app = FastAPI()

# Order matters — these run in sequence on every request:
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["api.leadforge.io", "localhost"])
app.add_middleware(CORSMiddleware, allow_origins=["https://app.leadforge.io"])
app.add_middleware(RequestLoggingMiddleware)     # structured JSON request logs
app.add_middleware(RateLimitMiddleware)          # Redis-backed sliding window
app.add_middleware(AuthMiddleware)               # JWT + API key validation
```

### Auth Dependency
```python
async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    
    scheme, token = authorization.split(" ", 1)
    
    if scheme.lower() == "bearer":
        # JWT token (web app users)
        payload = verify_jwt(token)
        user = await db.get(User, payload["sub"])
    elif scheme.lower() == "apikey":
        # API key (developer access)
        user = await get_user_by_api_key(token, db)
    else:
        raise HTTPException(401, "Invalid auth scheme")
    
    if not user:
        raise HTTPException(401, "Invalid credentials")
    
    return user
```

### Credit Guard Dependency
```python
async def require_credits(
    amount: float,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Atomic credit check + reserve
    result = await db.execute(
        text("UPDATE users SET credits = credits - :amount WHERE id = :id AND credits >= :amount RETURNING credits"),
        {"amount": amount, "id": user.id}
    )
    if not result.rowcount:
        raise HTTPException(402, "Insufficient credits")
    return user
```

---

## 12. Worker Services

### SMTP Worker Configuration

SMTP verification is the slowest and riskiest operation. Workers must be carefully managed:

```
SMTP Worker Pod:
  - 1 worker process
  - asyncio event loop handles 10 concurrent SMTP connections
  - Each connection uses a different source IP from the rotating pool
  - Max 100 SMTP connections per IP per hour (stay under spam thresholds)
  - IP health monitor: if IP gets 3 5xx rejections in 1 hour → quarantine for 4 hours
  
IP Rotation Pool:
  - MVP: 5 dedicated IPs on separate /32 subnets (Hetzner Cloud: $3/mo each)
  - Scale: 50+ IPs across multiple providers + ProxyMesh residential
  - SMTP sender domain: verify.leadforge.io (warmed up with DKIM/SPF/DMARC)
```

**Sender domain warming strategy:**
1. Register `verify.leadforge.io` with proper SPF, DKIM, DMARC
2. Week 1–2: No verification traffic, only outbound warmup emails from this domain
3. Week 3+: Gradually increase SMTP verification volume

### Scraper Worker Configuration

```
Scraper Worker Pod:
  - Playwright + Chromium (headless)
  - 1 browser instance per worker (Chromium is memory-heavy: ~300MB per instance)
  - Max 2 concurrent scraper workers on MVP (cost constraint)
  - Residential proxy: rotate IP per domain (via BrightData or Oxylabs ~$15/GB)
  - Screenshot on scrape failure for debug logging
```

---

## 13. Rate Limiting Strategy

### Sliding Window Rate Limiter (Redis)

```python
async def check_rate_limit(user_id: str, plan: str, redis: Redis) -> bool:
    limits = {
        "free":    {"rpm": 10,  "rpd": 50},
        "starter": {"rpm": 60,  "rpd": 1000},
        "growth":  {"rpm": 120, "rpd": 5000},
        "agency":  {"rpm": 300, "rpd": 20000},
    }
    
    limit = limits[plan]
    now = time.time()
    
    # Sliding window: count requests in last 60 seconds
    key = f"ratelimit:{user_id}:minute"
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - 60)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, 60)
    _, count, _, _ = await pipe.execute()
    
    if count >= limit["rpm"]:
        raise HTTPException(429, f"Rate limit exceeded: {limit['rpm']} requests/minute")
    
    # Daily limit check (similar pattern with 86400s window)
    ...
    
    return True
```

### Rate Limit Headers (returned on every response)

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 47
X-RateLimit-Reset: 1712345678
```

### SMTP-Specific Rate Limiting

Per-domain SMTP throttle to avoid triggering server-side blocks:

```
Key: smtp_throttle:{mx_host}
Value: request count in last 60 seconds
TTL: 60 seconds
Max: 30 SMTP probes per MX host per minute (across all workers)
```

If limit reached, task is requeued with 30-second delay.

---

## 14. Anti-Bot Considerations

### For Web Scraping (outbound — us scraping others)

- Playwright stealth mode (`playwright-stealth` package) — patches browser fingerprint leaks
- Randomized request timing: Gaussian distribution centered at 1.5s, σ=0.5s
- Rotate `User-Agent`, `Accept-Language`, `Accept-Encoding` headers
- Inject realistic `Referer` headers (e.g., Google search result URL)
- Respect `robots.txt` — parse and honor Crawl-delay and Disallow directives
- Residential proxy rotation — each domain gets a new IP after 5 requests
- Avoid scraping between 2–5 AM local time of the target server's likely timezone

### For Our Own API (inbound — preventing abuse)

- Rate limiting per user + per IP (unauthenticated requests: 20/hour by IP)
- CAPTCHA on signup (hCaptcha — privacy-friendly)
- Disposable email signup prevention (same blocklist as email verification)
- Fingerprint-based device tracking for free tier abuse detection
- Honeypot fields on signup form (bot detection)
- API key rotation required every 90 days (security best practice)

### SMTP Sender Reputation Protection

- Monitor IP reputation via MXToolbox and Talos Intelligence weekly
- Immediately rotate a blacklisted IP out of the pool
- Never verify more than 200 addresses per hour per IP
- Track per-domain rejection rates; if >30% rejections from a domain's MX → pause and flag for review
- Maintain feedback loop with major ISPs (Gmail Postmaster Tools, Microsoft SNDS)

---

## 15. Caching Strategy

### Redis Cache Keys

| Key Pattern | Value | TTL | Purpose |
|---|---|---|---|
| `mx:{domain}` | JSON array of MX hosts | 86,400s | MX record lookup |
| `catchall:{domain}` | "true" / "false" | 43,200s | Catch-all status |
| `disposable:{domain}` | "true" / "false" | In-memory (no Redis) | Disposable check |
| `domain_profile:{domain}` | JSON blob | 3,600s | Domain intelligence |
| `search_result:{hash}` | JSON result | 86,400s | Dedup same lookups |
| `ratelimit:{user_id}:minute` | Sorted set of timestamps | 60s | Rate limit |
| `ratelimit:{user_id}:day` | Sorted set of timestamps | 86,400s | Daily limit |
| `smtp_throttle:{mx_host}` | Integer count | 60s | SMTP throttling |

### Postgres Query Cache

- Use SQLAlchemy's built-in result caching for `domain_profiles` table
- Connection pooling via `asyncpg` with pool size of 10–20 connections per API pod
- Read replicas for dashboard/history queries (write goes to primary)

### CDN Cache (Vercel/CloudFront)

- Static assets: 1 year cache with content hash in filename
- API responses: never cached at CDN (always dynamic)
- Landing pages: ISR (Incremental Static Regeneration) — revalidate every 60s

---

## 16. Logging & Monitoring

### Structured Logging Format

Every log line is JSON:
```json
{
  "timestamp": "2026-03-19T10:23:41.123Z",
  "level": "info",
  "service": "api",
  "request_id": "req_abc123",
  "user_id": "usr_xyz",
  "endpoint": "POST /v1/discover",
  "duration_ms": 4231,
  "credits_used": 1,
  "domain": "acme.com",
  "smtp_status": "verified",
  "ip": "1.2.3.4"
}
```

### Metrics (Prometheus)

Expose `/metrics` endpoint on each service:

```
# Request metrics
http_requests_total{method, endpoint, status_code}
http_request_duration_seconds{endpoint, quantile}

# Business metrics
leadforge_searches_total{plan, verification_level}
leadforge_smtp_results_total{status}  # verified/invalid/unknown/timeout
leadforge_credits_consumed_total{plan}
leadforge_catch_all_domains_total

# SMTP worker metrics
smtp_worker_connections_active
smtp_worker_connections_per_ip{ip}
smtp_worker_rejections_total{mx_host, code}

# Queue metrics
celery_queue_length{queue}
celery_task_duration_seconds{task_name, quantile}
```

### Grafana Dashboards

1. **Operations Dashboard:** API latency p50/p95/p99, error rate, queue depth, worker health
2. **Business Dashboard:** Searches/hour, credits consumed, plan distribution, top domains searched
3. **SMTP Health Dashboard:** Per-IP rejection rates, catch-all rate by TLD, verification success rate

### Alerting Rules

| Alert | Condition | Severity |
|---|---|---|
| High API error rate | `error_rate > 5% for 5 minutes` | Critical |
| SMTP worker down | `smtp_worker_up == 0 for 2 minutes` | Critical |
| IP blacklisted | Any IP gets 0 successful verifications for 10 minutes | High |
| Queue backup | `celery_queue_length{queue="smtp"} > 1000 for 10 minutes` | High |
| Low credit pool | User credits < 10 (trigger upsell email) | Low |
| DB connection pool exhausted | `pg_pool_connections_available == 0 for 1 minute` | High |

### Error Tracking (Sentry)

Instrument both FastAPI (Sentry SDK) and Next.js (Sentry Browser SDK). Set up:
- Release tracking (tag releases with git SHA)
- Performance tracing (sample 10% of transactions)
- Alert on new error types within 5 minutes

---

## 17. Security Considerations

### API Security

- All traffic over TLS 1.3 (TLS 1.0/1.1 disabled at nginx level)
- API keys stored as bcrypt hashes (never stored in plaintext)
- JWT signed with RS256 (asymmetric) — private key in AWS Secrets Manager
- JWT expiry: 1 hour access token, 30-day refresh token (HTTP-only cookie)
- Request body size limit: 10MB (prevent memory exhaustion on bulk uploads)
- SQL injection: prevented by SQLAlchemy parameterized queries (never raw string concat)
- XSS: React escapes all output by default; CSP headers set
- CSRF: Samesite=Lax cookies + CSRF token for state-changing web requests

### Infrastructure Security

- VPC isolation: workers and DB in private subnet; only API pods in public subnet
- DB credentials rotated via AWS Secrets Manager auto-rotation
- S3 buckets: private ACL; signed URLs for file downloads (15-minute expiry)
- SSH access: only via SSM Session Manager (no public SSH ports)
- Container images: scanned with Trivy in CI/CD pipeline
- Dependency audit: `pip audit` + `npm audit` in CI
- Secrets: never in code or environment files; always via Secrets Manager

### Data Security

- Email results: searchable by user_id only (row-level isolation enforced at query layer)
- PII in logs: user emails and discovered emails are hashed before logging (`sha256(email)[:8]`)
- Encryption at rest: AWS RDS + S3 encryption enabled
- Backups: daily Postgres snapshots retained for 30 days

---

## 18. Hosting Architecture

### MVP Architecture (~$120/month)

```
Vercel (Free/Pro $20/mo)
  └─ Next.js frontend

Hetzner Cloud or AWS Lightsail (~$40/mo)
  └─ 1x CX31 (2 vCPU, 8GB RAM)
       ├─ Docker Compose
       │    ├─ FastAPI (2 uvicorn workers)
       │    ├─ Celery worker (SMTP + bulk + scrape in one)
       │    └─ Nginx reverse proxy
       └─ Mounted volume for temp files

Supabase ($25/mo)
  └─ Managed PostgreSQL

Redis Cloud (Free tier → $7/mo)
  └─ Managed Redis (30MB free, enough for MVP)

AWS S3 or Cloudflare R2 (~$1/mo at MVP volume)
  └─ CSV uploads + results

ProxyMesh or rotating IPs (~$30/mo)
  └─ 5 dedicated IPs for SMTP

Total MVP: ~$120/month
```

### Production Architecture (at scale)

```
AWS us-east-1 (primary) + eu-west-1 (GDPR compliance)

CloudFront CDN
  └─ Vercel frontend (static assets cached at edge)

API Layer (ECS Fargate or EKS):
  ├─ FastAPI pods: 2–10 pods (auto-scale on CPU + request count)
  └─ ALB (Application Load Balancer) with health checks

Worker Layer (ECS Fargate, separate task definitions):
  ├─ SMTP workers: 4–20 pods (scale on Redis queue depth)
  ├─ Scraper workers: 2–8 pods (Playwright needs 1vCPU + 1GB RAM each)
  └─ Bulk workers: 2–8 pods

Database Layer:
  ├─ RDS PostgreSQL (db.t3.medium → db.r6g.large as needed)
  │    ├─ Primary (write)
  │    └─ Read replica (read-heavy dashboard queries)
  └─ ElastiCache Redis (cache.t3.micro → cache.r6g.large)

Storage:
  └─ S3 (CSV files, worker output)

Proxy Infrastructure:
  ├─ Dedicated SMTP IPs: 20–50 IPs across Hetzner/OVH/Linode
  └─ Residential proxy pool: BrightData or Oxylabs (scraping)

Networking:
  ├─ VPC with public/private subnets
  ├─ NAT Gateway (workers in private subnet, egress via NAT)
  └─ Security groups: DB only accessible from API + worker SGs

Estimated cost at 100K searches/month: ~$800–1,200/month
```

---

## 19. Scaling to Millions of Searches

### Bottleneck Analysis

| Component | Bottleneck | Solution |
|---|---|---|
| SMTP verification | IP reputation + server rate limits | More IPs + smarter throttling |
| PostgreSQL | Write throughput at scale | Read replicas + TimescaleDB for time-series data |
| Redis | Memory for caching | Redis Cluster mode |
| Pattern generation | CPU-bound | Trivially fast; no scaling concern |
| Web scraping | Proxy cost + bot detection | More residential IPs + smarter evasion |

### Horizontal Scaling Plan

**0 → 10K searches/day (MVP):**
- Single server, Docker Compose, everything co-located
- 5 SMTP IPs, no read replica

**10K → 100K searches/day:**
- Split API + workers into separate VMs
- Add read replica to Postgres
- Increase SMTP IPs to 20
- Add Redis Cluster
- CDN for static assets

**100K → 1M searches/day:**
- Kubernetes (EKS) with HPA (Horizontal Pod Autoscaler) for API and SMTP workers
- Scale SMTP IPs to 100+
- Postgres: PgBouncer connection pooler in front of RDS
- Partition `searches` and `email_results` tables by month
- Introduce async result caching: if same email verified in last 7 days, return cached result without SMTP re-verification
- Consider managed verification API (Reoon, ZeroBounce) as fallback for spike handling

**1M+ searches/day:**
- Multi-region deployment (EU + US)
- Dedicated IP infrastructure (own /24 subnet)
- ML model for confidence scoring (trained on accumulated verified email data)
- Domain intelligence becomes a competitive moat (millions of verified patterns cached)
- Introduce Kafka for event streaming (search events → analytics pipeline)

### Database Partitioning Strategy

```sql
-- Partition searches by month for manageable table sizes
CREATE TABLE searches (
  ...
) PARTITION BY RANGE (created_at);

CREATE TABLE searches_2026_03 PARTITION OF searches
  FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Automate partition creation via pg_partman
```

### Result Cache Optimization at Scale

At millions of searches, the same domain + name combination will be searched repeatedly (especially for large companies). Implement a global result cache:

```
If same {first_name, last_name, domain} was searched by any user in last 48 hours:
  → Return cached results (no SMTP verification, 0 credit cost)
  → Mark result as "cached" in response
  → This should handle ~40% of all lookups at scale
```

This dramatically reduces SMTP load and IP reputation risk as search volume grows.
