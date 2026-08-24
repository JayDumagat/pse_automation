# PSE Daily Pulse

## Run with Docker

1. Start Docker Desktop and wait until the engine is running.
2. In PowerShell, from this folder:

```powershell
Copy-Item docker-compose.env.example .env
docker compose up --build
```

Open the dashboard at [http://localhost:8080](http://localhost:8080). The API is available at [http://localhost:8000/api](http://localhost:8000/api).

Stop the stack with:

```powershell
docker compose down
```

MongoDB and generated graphics persist in named Docker volumes. Remove them only when you intentionally want to erase local data:

```powershell
docker compose down -v
```

## API key

No API key is required. Market data is collected from PSE/Phisix, PSE Edge, TradingView, and Investagrams. Captions are manual input in the dashboard; no automatic LLM call is made.

## Services

- `mongo`: MongoDB 7 with a health check.
- `backend`: FastAPI, APScheduler, PSE ingestion, Mongo persistence, and Playwright Chromium graphics rendering.
- `frontend`: React production build served by Nginx; `/api` is reverse-proxied to the backend container.
