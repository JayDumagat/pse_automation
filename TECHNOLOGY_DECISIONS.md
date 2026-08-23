# TECHNOLOGY_DECISIONS.md

Every major component decision, per the mandate: reliability > loyalty to any suggested stack.

---

Component: Market quotes source
Candidates: Paid providers (EODHD, Twelve Data), PSE Edge scraping, Phisix community JSON API
Chosen: Phisix JSON API (phisix-api3/4.appspot.com) — primary
Reason: Free, official-mirror JSON of all ~390 PSE quotes (price, %change, volume); verified reachable from production container; no HTML parsing fragility. Retry + dual-host fallback built in.
Cost: Free
Risks: Community-run; mitigated by dual hosts + retries + validation gates.

---

Component: Index & sector data source
Candidates: Yahoo Finance chart API, TradingView scanner API, Google Finance scrape, PSE.com.ph admin-ajax
Chosen: TradingView scanner (single POST, all 8 indices) — primary; Yahoo Finance — fallback
Reason: Verified: 1 request returns PSEi + 6 sector indices + All Shares with close/change/high/low. Yahoo rate-limits bursts (observed 429s); kept as per-ticker fallback with backoff. Google Finance renders client-side (would need browser — rejected). PSE.com.ph ajax endpoints returned empty.
Cost: Free
Risks: Unofficial endpoints; dual-source redundancy mitigates.

---

Component: Dividend data source
Candidates: PSE Edge disclosure search, paid providers
Chosen: PSE Edge companyDisclosures/search.ax filtered by "Declaration of Cash Dividends" + detail-page parsing
Reason: Official source; verified parseable (company via SEC 17-C "Exact name of issuer", ex/record/payment dates via regex). Non-critical stage: failures degrade gracefully.
Cost: Free
Risks: HTML structure changes; regexes anchored on SEC form wording (stable for years).

---

Component: Database
Candidates: PostgreSQL, MongoDB
Chosen: MongoDB
Reason: Preconfigured in environment (zero ops); workload is daily document snapshots, run logs, content records — no relational joins needed at this scale. Problem statement explicitly permits substitution.
Cost: Included
Risks: None material at this scale.

---

Component: Backend language/API
Candidates: Python+FastAPI plus Node/TS API layer, single FastAPI
Chosen: Single FastAPI (Python 3.11) backend
Reason: Python owns data ingestion, validation (Pydantic), rendering (Playwright), and LLM calls; a second Node service adds deployment complexity with no benefit for a single-operator system.
Cost: Free
Risks: None.

---

Component: Data processing
Candidates: Polars, Pandas, NumPy, plain Python + Pydantic
Chosen: Plain Python + Pydantic
Reason: ~390 rows/day — DataFrame libraries are overkill (problem statement: "do not over-engineer"). All calculations deterministic pure Python; Pydantic validates every structure. No LLM math.
Cost: Free
Risks: None.

---

Component: Graphics renderer
Candidates: Canva API, Sharp, SVG+Resvg, HTML/CSS + Playwright screenshot
Chosen: HTML/CSS templates + Playwright Chromium screenshot -> PNG (1080x1350)
Reason: Fully automated, version-controlled templates (graphics_templates.py), deterministic rendering, accurate text/font control (Space Grotesk + Inter), zero external design-platform dependency. Canva's API requires costly plans for template autofill; rejected.
Cost: Free
Risks: Chromium memory — rendered sequentially in one browser session.

---

Component: Orchestration/scheduling
Candidates: n8n, Celery, Temporal, Prefect, cron, APScheduler
Chosen: APScheduler (in-process, cron trigger, Asia/Manila) + manual trigger endpoint
Reason: One daily DAG — dedicated workflow infra unjustified (problem statement agrees for small systems). Run/stage state persisted in MongoDB for observability.
Cost: Free
Risks: In-process (lost on restart) — zombie runs auto-marked failed on startup.

---

Component: Cache/queue
Candidates: Redis, none
Chosen: None (MongoDB only)
Reason: "If PostgreSQL alone is sufficient, avoid unnecessary infrastructure" — same logic applies to MongoDB. Job state lives in the runs collection; an asyncio lock prevents concurrent runs.
Cost: Saved
Risks: None at this scale.

---

Component: LLM provider
Candidates: OpenAI, Anthropic, Google direct keys; Emergent universal key
Chosen: Emergent universal key via emergentintegrations — provider/model switchable at runtime in Settings (OpenAI / Anthropic / Gemini)
Reason: User choice; single key covers all three providers = easy switching. Default: openai/gpt-5.4-mini (cost-efficient for captions). LLM receives only validated numbers.
Cost: Per-token from key balance
Risks: None; provider switch is one dropdown.

---

Component: Social publishing
Candidates: Meta Graph API, LinkedIn API, X API, review & export mode
Chosen: Review & Export mode (download PNGs, copy captions, track per-platform status)
Reason: No API credentials yet (user confirmed). Full pipeline + publishing records built; official API adapters can be added behind the same /api/publish contract later.
Cost: Free
Risks: Manual posting until credentials provided.

---

Component: Notifications
Candidates: Telegram, Discord, Slack, email, in-dashboard
Chosen: In-dashboard notification feed (user choice)
Reason: Zero external dependency; Telegram can be added later as a thin adapter over the same notifications collection.
Cost: Free
Risks: None.

---

Component: Frontend
Candidates: React+Vite, React CRA (environment template)
Chosen: React (CRA + craco) + Tailwind + shadcn/ui + Recharts + framer-motion
Reason: Environment-provided template with full shadcn component set; equivalent capability; fastest path.
Cost: Free
Risks: None.
