# plan.md — PSE Daily Market Automation

## 1. Objectives
- Ingest **real** daily PSE market data from free sources (primary: **Phisix** if reachable; fallback/enrichment: **PSE Edge**/official pages) with resilient fetching.
- Perform **deterministic** calculations + **Pydantic validation** for all key structures (no LLM math).
- Generate **5 social-ready PNG graphics** from version-controlled HTML/CSS templates via **Playwright**.
- Generate/edit **LLM captions** using **Emergent LLM** with **provider/model switching** exposed in Settings.
- Run a daily pipeline (APScheduler) and provide a lightweight **React dashboard** for run control, review/export, history, and notifications.
- Keep ops minimal: **MongoDB**, single **FastAPI** backend.

## 2. Implementation Steps

### Phase 1 — Core POC (isolation; do not proceed until green)
**Goal:** Prove scraping + validation + compute + render + LLM works with real data.
1. Web research (quick): confirm best current endpoints for **Phisix** + **PSE Edge JSON** patterns; note blockers/rate limits.
2. Create `test_core.py`:
   - Fetch market data (try Phisix `stocks.json`; if fails, PSE Edge/official fallback).
   - Parse into Pydantic models (quotes, market summary, movers, sector aggregates).
   - Compute: PSEi change (if index endpoint available; else compute “market breadth + turnover” and mark index as unavailable), top gainers/losers/most active, sector rollup, REIT subset (known ticker list), dividends (scrape PSE Edge dividend disclosures if reachable; else graceful “unavailable”).
   - Render 1–2 template types to PNG via Playwright (prove HTML→PNG pipeline + fonts).
   - LLM caption generation using `emergentintegrations` with **provider switch test** (at least 2 providers/models).
3. Iterate until POC acceptance:
   - Stable fetch (timeouts/retries/user-agent), consistent parsing, validations pass, images generated, captions generated.

**Phase 1 user stories**
1. As an operator, I can run a single script and fetch **real** PSE quotes successfully.
2. As an operator, I can see validated computed results (gainers/losers/actives) printed with no NaNs/None surprises.
3. As an operator, I can generate a PNG from an HTML template in one command.
4. As an operator, I can generate a caption from the LLM and see the exact validated numbers reflected.
5. As an operator, I can switch LLM provider/model and the script still returns captions.

---

### Phase 2 — V1 App Development (build around proven core)
**Backend (FastAPI + MongoDB + APScheduler)**
1. Project structure: `backend/app/{api,core,services,pipeline,models,db,templates,renderer,llm}`.
2. Data models (Pydantic): `MarketSummary`, `StockQuote`, `Movers`, `SectorSummary`, `REITSummary`, `DividendItem`, `Run`, `Notification`, `Settings`.
3. Ingestion services:
   - `sources/phisix.py` (primary quotes)
   - `sources/pse_edge.py` (dividends/disclosures + metadata if reachable)
   - Normalization layer to unify fields.
4. Pipeline orchestrator:
   - Stages: `fetch → validate → compute → store → graphics → captions → qa → approval_ready`.
   - Persist `runs` collection with per-stage timestamps, status, errors, artifact links.
   - APScheduler daily job + manual trigger endpoint.
5. Renderer:
   - HTML templates in `backend/templates/{market-summary,movers,sectors,reits,dividends}`.
   - Playwright screenshot service (1080×1350 default; optional 1080×1080).
   - Store PNGs (local `backend/storage/` + DB references).
6. LLM service:
   - Wrapper with Settings-driven provider/model; prompt templates per platform.
   - Regenerate endpoint uses stored validated numbers.
7. API endpoints (MVP set; `/api` prefix):
   - `GET /market/latest`, `GET /market/{date}`
   - `GET /stocks/top-gainers`, `/top-losers`, `/most-active`
   - `GET /reits`, `GET /dividends`
   - `GET /runs`, `POST /runs/trigger`, `POST /runs/{id}/regenerate`
   - `POST /publish` (review/export record only)
   - `GET/POST /settings`
   - `GET /notifications`

**Frontend (React CRA + Tailwind + shadcn/ui)**
8. Pages:
   - Today’s Market (PSEi/summary hero + movers tables + sectors strip)
   - Run Pipeline (trigger + stage progress)
   - Graphics (preview + download)
   - Captions (edit/copy/regenerate per platform)
   - Publishing (Review & Export: mark exported/published per platform)
   - Run History (status/duration/errors)
   - Settings (LLM provider/model, schedule time, branding basics)
   - Notifications feed (run events/errors)
9. UX essentials:
   - Clear run state (idle/running/failed/succeeded), stage-level logs.
   - “Data unavailable” handling for dividends/index without breaking the run.

**Phase 2 user stories**
1. As an operator, I open the dashboard and see **today’s** market summary from real scraped data.
2. As an operator, I click “Run Pipeline” and watch each stage complete with timestamps.
3. As an operator, I can preview and download all 5 generated PNG graphics.
4. As an operator, I can edit/copy/regenerate captions per platform.
5. As an operator, I can mark each platform as “Exported/Published” in review-export mode and see it tracked per run.

**End Phase 2:** run `testing_agent_v3` end-to-end (trigger run → validate data on UI → generate graphics → download → captions → export markers).

---

### Phase 3 — Hardening + Coverage
1. Improve scraping resilience: caching, backoff, multiple selectors/endpoints, source health status.
2. QA rules: detect suspicious values (e.g., negative turnover, impossible % changes), flag but don’t block export unless critical.
3. Better template system: theme tokens, shared components, consistent typography, faster render.
4. Add CSV export + API docs (OpenAPI tags) + seeded “known REIT tickers” management in Settings.

**Phase 3 user stories**
1. As an operator, I can see a clear warning when some data source is unavailable but still complete a partial run.
2. As an operator, I can download a CSV of movers and sector summaries for auditing.
3. As an operator, I can adjust the REIT ticker list in Settings and regenerate the REIT graphic.
4. As an operator, I can see QA flags for anomalies before exporting.
5. As an operator, I can rerun only graphics/captions without refetching data.

**End Phase 3:** run `testing_agent_v3` again for regression.

---

### Phase 4+ — Social API Wiring (when credentials exist)
1. Implement official publishing adapters (Meta Graph, LinkedIn, X) behind feature flags.
2. Token storage strategy + per-platform status reconciliation.

## 3. Next Actions
1. Implement **Phase 1** `test_core.py` and confirm reachable sources + data shapes.
2. Lock Pydantic schemas + compute functions once POC is stable.
3. Build V1 backend pipeline endpoints + MongoDB persistence.
4. Build React dashboard pages (minimal, connected) and confirm full core workflow.
5. Add templates for all 5 graphics and finalize review/export UX.

## 4. Success Criteria
- Phase 1: `test_core.py` consistently produces (a) validated computed outputs, (b) at least one PNG, (c) LLM caption with provider switch.
- Phase 2: From dashboard, a user can trigger a run and get **5 downloadable PNGs** + editable captions + export tracking saved to MongoDB.
- API returns correct latest data (`/api/market/latest`, movers, reits, dividends when available).
- Run history and notification feed show statuses/errors with timestamps; no mocks used.