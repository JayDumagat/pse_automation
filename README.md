# PSE Daily Pulse

## Deploy the dashboard to Vercel

The repository includes Vercel configuration for either Root Directory setting:
the repository root (`.`) or `frontend`. Both build the React dashboard and serve
its `build` output, including direct visits and refreshes on dashboard routes.
API requests and missing assets are not rewritten to HTML.

1. Import the repository into Vercel. Set Root Directory to `.` (or `frontend`)
   and Framework Preset to **Create React App**. Remove conflicting dashboard
   build/output overrides so the checked-in `vercel.json` supplies the commands.
2. Set `REACT_APP_BACKEND_URL` in Vercel's environment variables to the public
   HTTPS backend origin, for example `https://api.example.com`, without a trailing
   slash or `/api`. This is a public build-time value; redeploy after changing it.
3. On the backend, set `CORS_ORIGINS` to the exact dashboard origin, for example
   `https://your-project.vercel.app`. Multiple allowed origins are comma-separated.
4. Deploy the commit containing these files. Verify `/` and a direct visit to
   `/runs`, then confirm requests to the backend's `/api/` endpoint succeed.

This Vercel deployment hosts the frontend. Run the existing backend on a
persistent container host with MongoDB, Playwright Chromium, and graphics storage
(see the Docker setup below). Its in-process scheduler and background pipeline
require a running service. Vercel does not run this repository's Docker Compose
stack or Nginx API proxy. Without `REACT_APP_BACKEND_URL`, the dashboard will try
to call `/api` on its own Vercel domain, where no API is deployed.

If Vercel still displays `404 NOT_FOUND`, check that the domain points to a Ready
deployment of the correct project and commit, and that its build output includes
`index.html`. The error's request ID alone does not identify the cause.

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
