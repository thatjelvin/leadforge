# LeadForge — Product Requirements Document (PRD)
**Version:** 1.0  
**Status:** Ready for Engineering  
**Last Updated:** March 2026  
**Authors:** Product & Architecture Team

---

## Table of Contents

1. Product Overview
2. Problem Statement
3. Target Users
4. User Stories
5. Core Features
6. MVP Scope & Non-Goals
7. UX Flows
8. API Endpoints
9. Data Model
10. Success Metrics
11. Edge Cases
12. Compliance Considerations

---

## 1. Product Overview

LeadForge is a B2B SaaS platform for professional email discovery and verification. Given a person's name, company, and domain, LeadForge returns the most likely professional email address with a confidence score, along with ranked alternative permutations. The platform also supports bulk lead scraping from Google Maps, company websites, and public directories, with automated email discovery applied to each scraped contact.

**Core value proposition:** Sales teams, growth agencies, and founders can find verified, deliverable professional email addresses in seconds without manual research — at a fraction of the cost of Hunter.io or Apollo.

---

## 2. Problem Statement

Outbound sales depends on reaching the right person at the right email. The current landscape has three problems:

**Problem 1 — Discovery is slow.** Finding a professional email manually requires guessing formats, checking LinkedIn, scanning company websites, and trial-and-error. A skilled SDR spends 8–15 minutes per contact.

**Problem 2 — Existing tools are expensive.** Hunter.io charges $49/mo for 500 searches. Apollo bundles email into a bloated CRM. Clearbit is enterprise-only. There is no affordable, focused tool for small agencies and founder-led sales teams.

**Problem 3 — Unverified emails destroy deliverability.** Sending to bad addresses increases bounce rates, damages sender reputation, and can get a domain blacklisted. Most teams don't verify before sending.

LeadForge solves all three: fast discovery, accurate verification, and affordable pricing.

---

## 3. Target Users

### Primary: Sales Development Representatives (SDRs)
- Run 50–200 outbound touches per week
- Need verified emails fast, in bulk
- Care about bounce rate and sender reputation
- Already use tools like Apollo, Instantly, Smartlead

### Secondary: Growth & Lead Generation Agencies
- Manage outbound for 5–30 clients simultaneously
- Need white-label or API access
- Resell lead lists; accuracy is their core product quality metric
- Value bulk operations and CSV export

### Tertiary: Founders & Solo Operators
- Doing founder-led sales
- Small budgets, high intent
- Want a focused tool, not a bloated CRM
- Will use the UI, not the API

### Quaternary: Developers & Integrators
- Building sales automation workflows (n8n, Make, Zapier)
- Need a clean REST API with predictable pricing
- Care about rate limits, reliability, and JSON structure

---

## 4. User Stories

### Email Discovery
- **US-01:** As an SDR, I want to input a person's name, company, and domain so I can get the most likely email address instantly.
- **US-02:** As an SDR, I want to see a confidence score per email so I know how likely it is to be correct before sending.
- **US-03:** As an agency operator, I want to upload a CSV of contacts and get enriched emails back in bulk so I can process hundreds of leads at once.
- **US-04:** As a developer, I want a REST API endpoint that accepts name/domain and returns email permutations with scores so I can integrate into my n8n workflows.

### Email Verification
- **US-05:** As an SDR, I want each returned email to show a validity status (verified, risky, invalid) so I never send to dead addresses.
- **US-06:** As an agency operator, I want catch-all domains flagged so I know when verification is unreliable.
- **US-07:** As a founder, I want disposable/temporary email addresses detected and filtered out automatically.

### Lead Scraping
- **US-08:** As an agency operator, I want to enter a business type and city (e.g., "HVAC companies in Austin, TX") and get a list of businesses with contact names and discovered emails.
- **US-09:** As an SDR, I want to input a company website and have LeadForge scrape it for contact pages and return email addresses found.
- **US-10:** As an agency operator, I want scraped leads exported to CSV or pushed directly to a Google Sheet.

### Account & Billing
- **US-11:** As a user, I want a credit-based system so I only pay for what I use.
- **US-12:** As an agency, I want to create a team account with shared credits and usage tracking per team member.
- **US-13:** As a developer, I want API keys scoped to my account with per-key usage tracking.

---

## 5. Core Features

### 5.1 Email Pattern Generator

LeadForge generates all standard professional email permutations from a given first name, last name, and domain.

**Standard patterns generated (priority order):**

| Pattern | Example |
|---|---|
| firstname.lastname | john.smith@acme.com |
| firstnamelastname | johnsmith@acme.com |
| firstname | john@acme.com |
| flastname | jsmith@acme.com |
| firstnamel | johns@acme.com |
| f.lastname | j.smith@acme.com |
| firstname_lastname | john_smith@acme.com |
| lastname.firstname | smith.john@acme.com |
| lastname | smith@acme.com |
| lastnameF | smithj@acme.com |

**Pattern weighting:** LeadForge detects the domain's predominant email pattern by cross-referencing previously verified emails for that domain stored in its database. If 80% of verified addresses at acme.com use `firstname.lastname`, that pattern gets a base confidence boost of +30 points for new lookups against that domain.

### 5.2 Email Verification Engine

Each candidate email is run through a multi-stage verification pipeline:

**Stage 1 — Syntax Validation**
- RFC 5321/5322 format check
- Reject malformed local parts and domains
- Latency: <1ms

**Stage 2 — Domain/MX Record Check**
- DNS lookup to confirm domain exists
- MX record lookup to confirm domain accepts mail
- Cache MX results for 24 hours per domain
- Latency: 50–200ms

**Stage 3 — Disposable Email Detection**
- Check against maintained blocklist of ~100,000 known disposable email providers (mailinator, guerrilla mail, etc.)
- Latency: <1ms (in-memory lookup)

**Stage 4 — Catch-All Detection**
- Send SMTP probe to a randomly generated address (e.g., `zxq9k2@domain.com`)
- If server accepts → domain is catch-all; flag all results as "Unverifiable – Catch-All"
- Cache catch-all status per domain for 12 hours
- Latency: 1–3 seconds

**Stage 5 — SMTP Handshake Verification**
- Open TCP connection to MX server on port 25 (or 587)
- Send EHLO → MAIL FROM (use rotating pool of sender domains) → RCPT TO
- Parse SMTP response code:
  - 250 → Valid (Verified)
  - 550/551/553 → Invalid (does not exist)
  - 421/450/451/452 → Greylisted or temp failure → retry once
  - 5xx other → Unknown
- Close connection without sending DATA (no email sent)
- Rotate source IPs and sender domains to avoid blacklisting
- Latency: 2–8 seconds

**Confidence Score Calculation:**

```
base_score = pattern_popularity_score (0–40)
+ domain_pattern_match_bonus (0–30)  // if domain pattern known
+ smtp_result_bonus (verified=+30, invalid=-60, unknown=0)
- catch_all_penalty (catch_all domain = -20)
- disposable_penalty (disposable = -100, clamped to 0)

final_score = clamp(base_score, 0, 100)
```

### 5.3 Domain Intelligence

For each searched domain, LeadForge builds and caches a Domain Profile:
- Detected predominant email pattern
- MX provider (Google Workspace, Microsoft 365, custom)
- Catch-all status
- Number of verified emails found for this domain
- Domain age and registrar (from WHOIS)

This profile improves accuracy for all future searches against the same domain.

### 5.4 Bulk Search

- CSV upload: columns mapped to name, company, domain
- Maximum 10,000 rows per upload on paid plans
- Processed asynchronously via job queue
- Results downloadable as CSV or exportable via webhook
- Real-time progress via WebSocket or polling endpoint

### 5.5 Lead Scraper

**Google Maps Scraper**
- Input: business category + location (e.g., "dentists in Chicago, IL")
- Scrapes Google Maps search results via Playwright (headless browser)
- Extracts: business name, website, phone number
- Then runs email discovery against extracted website domain
- Returns enriched lead list

**Website Contact Scraper**
- Input: company website URL
- Crawls /contact, /about, /team pages
- Extracts: email addresses (regex), names (heuristic extraction near email patterns)
- Also checks page metadata and schema.org markup

**Public Directory Scraper**
- Scrapes Yelp, Yellow Pages, Clutch, G2 for business contact info
- Rate-limited with rotating user agents and proxy rotation

**LinkedIn Enrichment (Limited)**
- If LinkedIn URL is provided as input, extract public profile data
- Name, job title, company confirmation
- Does NOT scrape private data; uses only publicly visible profile fields
- Respects robots.txt; recommend users use LeadForge's LinkedIn integration via official methods where possible

### 5.6 API

Full REST API available on Starter plan and above. See Section 8 for endpoints.

### 5.7 Integrations

**MVP integrations:**
- CSV export
- Webhook delivery (POST results to user-defined URL)
- Google Sheets export (OAuth)

**Post-MVP:**
- Zapier / Make native apps
- HubSpot CRM push
- Instantly / Smartlead direct integration

---

## 6. MVP Scope & Non-Goals

### MVP (v1.0) — Ship in 8 Weeks

**In scope:**
- Single email lookup UI (name + company + domain → results)
- Email pattern generation (all 10 patterns)
- Full 5-stage verification pipeline
- Domain intelligence caching
- Bulk CSV upload (up to 500 rows on MVP)
- REST API (3 core endpoints)
- Credit-based billing via Stripe
- Basic dashboard (usage, history, credits)
- Google Maps lead scraper (single pipeline)
- CSV export

**Not in scope for MVP:**
- LinkedIn scraper (legal complexity, defer)
- Team/multi-seat accounts (post-MVP)
- CRM integrations (post-MVP)
- White-label mode (post-MVP)
- Zapier / Make apps (post-MVP)
- Advanced analytics (post-MVP)
- Public directory scrapers beyond Google Maps (post-MVP)
- Email warm-up or sending capabilities (never — out of product scope)

### Non-Goals (Permanent)
- LeadForge will never send emails on behalf of users
- LeadForge will never store scraped data beyond what is needed to serve results and build domain profiles
- LeadForge will never scrape data from behind authentication walls
- LeadForge will never provide data that violates GDPR data subject rights upon request

---

## 7. UX Flows

### Flow 1: Single Email Lookup

```
[Landing Page]
      ↓
[Sign Up / Log In]
      ↓
[Dashboard — Home]
      ↓
[Search Bar: Name | Company | Domain | LinkedIn URL (optional)]
      ↓ (submit)
[Loading state: "Generating patterns..." → "Verifying..." — 3–8 seconds]
      ↓
[Results Page]
  ┌─────────────────────────────────────────────┐
  │ ✅ john.smith@acme.com     Verified  92%    │
  │ ⚠️  jsmith@acme.com        Possible  67%    │
  │ 🔴  john@acme.com          Low prob  21%    │
  │                                              │
  │ [Copy] [Export] [Save to List]               │
  └─────────────────────────────────────────────┘
      ↓
[Optional: Add to Lead List]
```

### Flow 2: Bulk CSV Upload

```
[Dashboard → Bulk Search]
      ↓
[Upload CSV — drag/drop or file picker]
      ↓
[Column Mapper UI — map CSV headers to: First Name, Last Name, Company, Domain]
      ↓
[Confirm & Start — shows credit cost estimate]
      ↓
[Job Queue — progress bar, estimated completion time]
      ↓
[Results Ready — email notification + in-app notification]
      ↓
[Download CSV or Export to Google Sheets]
```

### Flow 3: Google Maps Lead Scraper

```
[Dashboard → Lead Scraper]
      ↓
[Input: Business Type | City, State]
  e.g., "HVAC companies | Austin, TX"
      ↓
[Preview: "Estimated ~45 leads found — will use ~90 credits"]
      ↓
[Confirm & Run]
      ↓
[Async job — shows progress]
      ↓
[Results table: Business Name | Website | Phone | Discovered Email | Confidence]
      ↓
[Export CSV | Push to Google Sheets | Save to List]
```

### Flow 4: API Integration

```
Developer creates API key in Settings
      ↓
Makes POST /v1/discover with {first_name, last_name, domain}
      ↓
Receives JSON response with ranked permutations + verification status
      ↓
(Optionally) polls GET /v1/jobs/{id} for async bulk results
```

---

## 8. API Endpoints

**Base URL:** `https://api.leadforge.io/v1`  
**Authentication:** `Authorization: Bearer {api_key}`  
**Content-Type:** `application/json`

---

### POST /v1/discover

Discover and verify email addresses for a single contact.

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "domain": "acme.com",
  "company": "Acme Inc",          // optional, improves pattern matching
  "linkedin_url": "https://...",  // optional
  "verification_level": "full"    // "syntax" | "mx" | "full" (default: full)
}
```

**Response (200):**
```json
{
  "request_id": "req_abc123",
  "credits_used": 1,
  "domain_profile": {
    "domain": "acme.com",
    "mx_provider": "google",
    "is_catch_all": false,
    "predominant_pattern": "firstname.lastname",
    "pattern_confidence": 0.84
  },
  "results": [
    {
      "email": "john.smith@acme.com",
      "confidence": 92,
      "status": "verified",
      "smtp_response": 250,
      "pattern": "firstname.lastname",
      "is_primary": true
    },
    {
      "email": "jsmith@acme.com",
      "confidence": 67,
      "status": "possible",
      "smtp_response": null,
      "pattern": "flastname",
      "is_primary": false
    },
    {
      "email": "john@acme.com",
      "confidence": 21,
      "status": "low_probability",
      "smtp_response": null,
      "pattern": "firstname",
      "is_primary": false
    }
  ]
}
```

**Error responses:**
- `400` — missing required fields or invalid domain
- `402` — insufficient credits
- `422` — domain has no MX records (undeliverable)
- `429` — rate limit exceeded
- `503` — SMTP verification temporarily unavailable

---

### POST /v1/verify

Verify a known email address without discovery.

**Request:**
```json
{
  "email": "john.smith@acme.com",
  "verification_level": "full"
}
```

**Response (200):**
```json
{
  "email": "john.smith@acme.com",
  "status": "verified",
  "sub_status": null,
  "is_disposable": false,
  "is_catch_all": false,
  "mx_found": true,
  "smtp_valid": true,
  "confidence": 94,
  "credits_used": 0.5
}
```

---

### POST /v1/bulk

Submit a bulk discovery job.

**Request:**
```json
{
  "contacts": [
    { "first_name": "John", "last_name": "Smith", "domain": "acme.com" },
    { "first_name": "Jane", "last_name": "Doe", "domain": "example.com" }
  ],
  "webhook_url": "https://your-app.com/webhook",  // optional
  "verification_level": "full"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "job_xyz789",
  "status": "queued",
  "total_contacts": 2,
  "estimated_credits": 2,
  "estimated_completion_seconds": 30,
  "poll_url": "/v1/jobs/job_xyz789"
}
```

---

### GET /v1/jobs/{job_id}

Poll status of a bulk job.

**Response (200):**
```json
{
  "job_id": "job_xyz789",
  "status": "completed",   // queued | processing | completed | failed
  "progress": 100,
  "total": 2,
  "completed": 2,
  "failed": 0,
  "download_url": "https://api.leadforge.io/v1/jobs/job_xyz789/results.csv",
  "results": [ /* same structure as /v1/discover results, per contact */ ]
}
```

---

### POST /v1/scrape/maps

Trigger a Google Maps lead scrape job.

**Request:**
```json
{
  "query": "HVAC companies",
  "location": "Austin, TX",
  "max_results": 50,
  "auto_discover_emails": true,
  "webhook_url": "https://your-app.com/webhook"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "scrape_abc456",
  "status": "queued",
  "estimated_leads": 45,
  "estimated_credits": 90,
  "poll_url": "/v1/jobs/scrape_abc456"
}
```

---

### GET /v1/account

Return current account status.

**Response (200):**
```json
{
  "plan": "starter",
  "credits_remaining": 847,
  "credits_used_this_month": 153,
  "api_calls_today": 42,
  "rate_limit": {
    "requests_per_minute": 60,
    "bulk_rows_per_job": 500
  }
}
```

---

## 9. Data Model

### users
```sql
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  name          TEXT,
  plan          TEXT NOT NULL DEFAULT 'free',  -- free | starter | growth | agency
  credits       INTEGER NOT NULL DEFAULT 50,
  api_key       TEXT UNIQUE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### searches
```sql
CREATE TABLE searches (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES users(id),
  first_name    TEXT,
  last_name     TEXT,
  company       TEXT,
  domain        TEXT NOT NULL,
  linkedin_url  TEXT,
  credits_used  NUMERIC(4,2),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### email_results
```sql
CREATE TABLE email_results (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  search_id       UUID REFERENCES searches(id),
  email           TEXT NOT NULL,
  pattern         TEXT,
  confidence      INTEGER,
  status          TEXT,   -- verified | possible | low_probability | invalid | catch_all
  smtp_response   INTEGER,
  is_primary      BOOLEAN DEFAULT FALSE,
  verified_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### domain_profiles
```sql
CREATE TABLE domain_profiles (
  domain                  TEXT PRIMARY KEY,
  mx_provider             TEXT,
  mx_records              JSONB,
  is_catch_all            BOOLEAN,
  catch_all_checked_at    TIMESTAMPTZ,
  predominant_pattern     TEXT,
  pattern_confidence      NUMERIC(4,3),
  verified_email_count    INTEGER DEFAULT 0,
  domain_age_years        NUMERIC(5,1),
  last_updated            TIMESTAMPTZ DEFAULT NOW()
);
```

### bulk_jobs
```sql
CREATE TABLE bulk_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id),
  type            TEXT,   -- discovery | verification | scrape_maps
  status          TEXT,   -- queued | processing | completed | failed
  total_contacts  INTEGER,
  completed       INTEGER DEFAULT 0,
  failed          INTEGER DEFAULT 0,
  input_file_url  TEXT,
  output_file_url TEXT,
  webhook_url     TEXT,
  credits_used    INTEGER,
  error_message   TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  completed_at    TIMESTAMPTZ
);
```

### scraped_leads
```sql
CREATE TABLE scraped_leads (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id          UUID REFERENCES bulk_jobs(id),
  business_name   TEXT,
  website         TEXT,
  phone           TEXT,
  address         TEXT,
  source          TEXT,   -- google_maps | yelp | website | directory
  raw_emails      TEXT[],
  discovered_email TEXT,
  confidence      INTEGER,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### credit_transactions
```sql
CREATE TABLE credit_transactions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES users(id),
  amount        INTEGER NOT NULL,  -- negative = spend, positive = purchase/refund
  type          TEXT,   -- purchase | usage | refund | bonus
  reference_id  UUID,   -- search_id or job_id
  note          TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 10. Success Metrics

### Product Quality
- **Email accuracy rate:** ≥75% of "verified" emails are truly deliverable (measured via user feedback and bounce reports)
- **Catch-all detection rate:** ≥95% of catch-all domains correctly flagged
- **SMTP verification speed:** p95 < 8 seconds per single lookup
- **False positive rate:** <5% (verified emails that actually bounce)

### Growth
- **Month 1:** 500 signups, 50 paying users
- **Month 3:** 2,000 signups, 200 paying users, $5K MRR
- **Month 6:** 5,000 signups, 500 paying users, $15K MRR
- **Churn:** <8% monthly on paid plans

### Engagement
- **Activation rate:** ≥60% of signups run at least 1 search within 7 days
- **API adoption:** ≥25% of Starter+ users make at least 1 API call per month
- **Bulk usage:** ≥30% of Growth+ users run at least 1 bulk job per month

### Operations
- **Uptime:** ≥99.5% for API, ≥99.9% for SMTP workers
- **SMTP worker blacklist rate:** <1% of IPs blacklisted per month
- **Support ticket rate:** <2% of active users per month

---

## 11. Edge Cases

| Edge Case | Handling |
|---|---|
| Domain has no MX records | Return immediately with status `no_mx`; no credits charged |
| Domain is catch-all | Flag all results as `unverifiable_catch_all`; reduce credit cost to 0.25 |
| SMTP server rate-limits verification | Retry once after 10s; if still rate-limited, return status `smtp_timeout` |
| Person has non-Latin name characters | Normalize to ASCII equivalents (e.g., é → e); log original for future ML |
| Single-part names (mononym) | Treat as first name; generate patterns using only first_name component |
| Company has multiple domains | Allow user to specify domain; do not auto-guess |
| Very large domains (Google, Microsoft) | Always return `catch_all` — major providers accept all inbound; skip SMTP |
| Port 25 blocked by cloud provider | Fall back to port 587; if also blocked, return `smtp_unavailable` |
| Greylisting | Retry after 30s delay once; if still greylisted, return `greylist_detected` |
| User uploads CSV with 10,000+ rows | Cap at plan limit; reject remainder with clear error message |
| Google Maps returns 0 results | Return empty job result; charge 0 credits |
| LinkedIn URL provided but profile is private | Ignore LinkedIn input; proceed with name/domain only |
| Domain is disposable email provider | Return status `disposable_domain`; 0 credits charged |

---

## 12. Compliance Considerations

### GDPR (EU General Data Protection Regulation)

LeadForge collects and processes personal data (email addresses, names) of EU residents. Compliance requirements:

- **Lawful basis:** LeadForge's lawful basis is Legitimate Interest (Art. 6(1)(f) GDPR) — processing professional contact data for B2B sales outreach is a recognized legitimate interest under GDPR's recital 47, consistent with established precedent from supervisory authorities.
- **Data minimization:** LeadForge only stores the minimum data needed: the discovered email, confidence score, and domain profile. Raw scraped content is not persisted.
- **Right to erasure:** Users can submit erasure requests via /account/delete or by emailing privacy@leadforge.io. All personal data deleted within 30 days.
- **Data subject access requests:** Supported via account settings panel within 30 days.
- **Data Processing Agreement (DPA):** Available for B2B customers upon request.
- **No special category data:** LeadForge only processes professional contact information, not health, political, or other special category data.
- **Transfer mechanisms:** EU users' data stored in EU-region (AWS eu-west-1). No cross-border transfers without SCCs in place.

### CAN-SPAM Act (USA)

LeadForge is a data tool, not an email sender. However, users sending outbound using LeadForge-discovered addresses must comply with CAN-SPAM. LeadForge's Terms of Service require users to:
- Only send to addresses in professional B2B contexts
- Include an opt-out mechanism in all outbound emails
- Not use LeadForge data for spam or unsolicited consumer emails

LeadForge itself complies with CAN-SPAM for any transactional emails it sends to its own users.

### CCPA (California Consumer Privacy Act)

- LeadForge does not sell personal data to third parties.
- California residents can request deletion of their personal data.
- Privacy policy clearly states data collection and use practices.

### Anti-Scraping / Terms of Service Compliance

- **Google Maps:** Scraping Google Maps may violate Google's Terms of Service. For MVP, we use a rate-limited, IP-rotated approach consistent with general web crawling norms. Post-MVP, evaluate Google Maps Platform API for compliant data access.
- **LinkedIn:** LinkedIn explicitly prohibits scraping. LeadForge will only use publicly visible profile data when a user manually provides a LinkedIn URL. LeadForge will not build an automated LinkedIn scraping pipeline.
- **Company websites:** LeadForge respects `robots.txt` and `Crawl-delay` directives. Scraped data is used only to return results to the requesting user.

### Data Retention Policy

| Data Type | Retention |
|---|---|
| Search history | 12 months, then anonymized |
| Email results | 12 months |
| Domain profiles | Indefinite (operational data) |
| Scraped lead data | 90 days, then deleted |
| Billing records | 7 years (legal requirement) |
| API logs | 90 days |

### Prohibited Use Policy

LeadForge's Terms of Service explicitly prohibit:
- Using discovered emails for consumer spam or phishing
- Reselling raw data from LeadForge as a standalone product
- Scraping LeadForge's own database
- Using LeadForge to harvest emails for bulk unsolicited consumer outreach
- Attempting to discover emails for government officials, minors, or private individuals without professional context

Violations result in immediate account termination and IP ban.
