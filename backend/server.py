"""PSE Daily Pulse — FastAPI backend.
Pipeline: fetch -> validate -> compute -> store -> graphics -> captions -> qa -> ready
"""
import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import pipeline  # noqa: E402
import renderer  # noqa: E402
from models import AVAILABLE_MODELS, GRAPHIC_TYPES, PLATFORMS, SettingsModel  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("server")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="PSE Daily Pulse API")
api = APIRouter(prefix="/api")

scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Manila"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------- request models -------------------------
class PublishRequest(BaseModel):
    run_id: str
    platform: str
    status: str  # pending | exported | published
    note: Optional[str] = ""


class CaptionUpdate(BaseModel):
    text: str


class ApproveRequest(BaseModel):
    approved: bool


class RegenerateRequest(BaseModel):
    target: str = "all"  # graphics | captions | all


# ------------------------- health -------------------------
@api.get("/")
async def root():
    return {"message": "PSE Daily Pulse API", "status": "ok"}


# ------------------------- market data -------------------------
async def _latest_snapshot():
    return await db.snapshots.find_one({}, {"_id": 0}, sort=[("created_at", -1)])


@api.get("/market/latest")
async def market_latest():
    snap = await _latest_snapshot()
    latest_run = await db.runs.find_one({}, {"_id": 0}, sort=[("started_at", -1)])
    market_closed = False
    if snap:
        try:
            manila_today = datetime.now(ZoneInfo("Asia/Manila")).date().isoformat()
            market_closed = (datetime.now(ZoneInfo("Asia/Manila")).weekday() >= 5
                             or snap["market_date"] != manila_today)
        except Exception:
            pass
    return {"snapshot": snap, "latest_run": latest_run, "market_closed": market_closed}


@api.get("/market/{market_date}")
async def market_by_date(market_date: str):
    snap = await db.snapshots.find_one({"market_date": market_date}, {"_id": 0}, sort=[("created_at", -1)])
    if not snap:
        raise HTTPException(404, f"No snapshot for {market_date}")
    return snap


@api.get("/stocks/top-gainers")
async def top_gainers(limit: int = 10):
    snap = await _latest_snapshot()
    return (snap or {}).get("gainers", [])[:limit]


@api.get("/stocks/top-losers")
async def top_losers(limit: int = 10):
    snap = await _latest_snapshot()
    return (snap or {}).get("losers", [])[:limit]


@api.get("/stocks/most-active")
async def most_active(limit: int = 10):
    snap = await _latest_snapshot()
    return (snap or {}).get("actives", [])[:limit]


@api.get("/sectors")
async def sectors():
    snap = await _latest_snapshot()
    return (snap or {}).get("sectors", [])


@api.get("/reits")
async def reits():
    snap = await _latest_snapshot()
    return (snap or {}).get("reits", [])


@api.get("/dividends")
async def dividends():
    snap = await _latest_snapshot()
    return (snap or {}).get("dividends", [])


# ------------------------- runs -------------------------
@api.post("/runs/trigger")
async def trigger_run():
    if pipeline.RUN_LOCK.locked():
        raise HTTPException(409, "A run is already in progress")
    run_id = await pipeline.create_run(db, trigger="manual")
    asyncio.create_task(pipeline.run_pipeline(db, run_id))
    return {"run_id": run_id, "status": "running"}


@api.get("/runs")
async def list_runs(limit: int = 50, status: Optional[str] = None):
    query = {"status": status} if status else {}
    runs = await db.runs.find(query, {"_id": 0}).sort("started_at", -1).to_list(limit)
    return runs


@api.get("/runs/latest")
async def latest_run():
    run = await db.runs.find_one({}, {"_id": 0}, sort=[("started_at", -1)])
    if not run:
        return None
    return run


@api.get("/runs/{run_id}")
async def get_run(run_id: str):
    run = await db.runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@api.post("/runs/{run_id}/regenerate")
async def regenerate(run_id: str, body: RegenerateRequest):
    run = await db.runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Run not found")
    results = {}
    try:
        if body.target in ("graphics", "all"):
            results["graphics"] = await pipeline.regenerate_graphics(db, run_id)
        if body.target in ("captions", "all"):
            results["captions"] = await pipeline.regenerate_all_captions(db, run_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"run_id": run_id, "regenerated": results}


@api.delete("/runs")
async def clear_all_runs():
    """Danger zone: wipe all runs and artifacts."""
    await db.runs.delete_many({})
    await db.snapshots.delete_many({})
    await db.graphics.delete_many({})
    await db.captions.delete_many({})
    await db.publishing.delete_many({})
    await db.notifications.delete_many({})
    shutil.rmtree(renderer.STORAGE_DIR, ignore_errors=True)
    return {"cleared": True}


# ------------------------- graphics -------------------------
@api.get("/runs/{run_id}/graphics")
async def run_graphics(run_id: str):
    return await db.graphics.find({"run_id": run_id}, {"_id": 0}).to_list(20)


@api.get("/graphics/file/{run_id}/{gtype}")
async def graphic_file(run_id: str, gtype: str, download: bool = False):
    if gtype not in GRAPHIC_TYPES:
        raise HTTPException(400, "Unknown graphic type")
    path = renderer.graphic_path(run_id, gtype)
    if not path.exists():
        raise HTTPException(404, "Graphic not found")
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="pse-daily-{gtype}.png"'
    return FileResponse(str(path), media_type="image/png", headers=headers)


@api.patch("/graphics/{run_id}/{gtype}/approve")
async def approve_graphic(run_id: str, gtype: str, body: ApproveRequest):
    res = await db.graphics.update_one({"run_id": run_id, "type": gtype},
                                       {"$set": {"approved": body.approved}})
    if res.matched_count == 0:
        raise HTTPException(404, "Graphic not found")
    return {"run_id": run_id, "type": gtype, "approved": body.approved}


# ------------------------- captions -------------------------
@api.get("/runs/{run_id}/captions")
async def run_captions(run_id: str):
    return await db.captions.find({"run_id": run_id}, {"_id": 0}).to_list(10)


@api.put("/runs/{run_id}/captions/{platform}")
async def update_caption(run_id: str, platform: str, body: CaptionUpdate):
    if platform not in PLATFORMS:
        raise HTTPException(400, "Unknown platform")
    res = await db.captions.update_one(
        {"run_id": run_id, "platform": platform},
        {"$set": {"text": body.text, "edited": True, "updated_at": now_iso()}})
    if res.matched_count == 0:
        # allow creating caption if generation failed earlier
        await db.captions.insert_one({
            "id": str(uuid.uuid4()), "run_id": run_id, "platform": platform,
            "text": body.text, "provider": "manual", "model": "manual",
            "edited": True, "updated_at": now_iso()})
    doc = await db.captions.find_one({"run_id": run_id, "platform": platform}, {"_id": 0})
    return doc


@api.post("/runs/{run_id}/captions/{platform}/regenerate")
async def regenerate_caption_ep(run_id: str, platform: str):
    if platform not in PLATFORMS:
        raise HTTPException(400, "Unknown platform")
    snap = await db.snapshots.find_one({"run_id": run_id}, {"_id": 0})
    if not snap:
        raise HTTPException(400, "No snapshot for this run")
    settings = await pipeline.get_settings(db)
    import llm_service
    try:
        text = await llm_service.regenerate_caption(snap, platform, settings.llm_provider, settings.llm_model)
    except Exception as e:
        raise HTTPException(502, f"LLM generation failed: {e}")
    await db.captions.update_one(
        {"run_id": run_id, "platform": platform},
        {"$set": {"text": text, "provider": settings.llm_provider, "model": settings.llm_model,
                  "edited": False, "updated_at": now_iso()},
         "$setOnInsert": {"id": str(uuid.uuid4()), "run_id": run_id, "platform": platform}},
        upsert=True)
    doc = await db.captions.find_one({"run_id": run_id, "platform": platform}, {"_id": 0})
    return doc


# ------------------------- publishing -------------------------
@api.get("/runs/{run_id}/publishing")
async def run_publishing(run_id: str):
    return await db.publishing.find({"run_id": run_id}, {"_id": 0}).to_list(10)


@api.post("/publish")
async def publish(body: PublishRequest):
    if body.platform not in PLATFORMS:
        raise HTTPException(400, "Unknown platform")
    if body.status not in ("pending", "exported", "published"):
        raise HTTPException(400, "Invalid status")
    res = await db.publishing.update_one(
        {"run_id": body.run_id, "platform": body.platform},
        {"$set": {"status": body.status, "note": body.note or "", "updated_at": now_iso()},
         "$setOnInsert": {"id": str(uuid.uuid4()), "run_id": body.run_id, "platform": body.platform}},
        upsert=True)
    await pipeline.notify(db, "info", f"{body.platform.capitalize()} marked {body.status}",
                          f"Publishing status updated to '{body.status}' (review & export mode).", body.run_id)
    doc = await db.publishing.find_one({"run_id": body.run_id, "platform": body.platform}, {"_id": 0})
    return doc


# ------------------------- notifications -------------------------
@api.get("/notifications")
async def notifications(limit: int = 30):
    items = await db.notifications.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    unread = await db.notifications.count_documents({"read": False})
    return {"items": items, "unread": unread}


@api.post("/notifications/mark-read")
async def mark_notifications_read():
    await db.notifications.update_many({"read": False}, {"$set": {"read": True}})
    return {"ok": True}


# ------------------------- settings -------------------------
@api.get("/settings")
async def get_settings_ep():
    settings = await pipeline.get_settings(db)
    return settings.model_dump()


@api.put("/settings")
async def update_settings(body: SettingsModel):
    if body.llm_provider not in AVAILABLE_MODELS:
        raise HTTPException(400, "Unknown provider")
    if body.llm_model not in AVAILABLE_MODELS[body.llm_provider]:
        raise HTTPException(400, f"Model not available for {body.llm_provider}")
    try:
        hh, mm = body.schedule_time.split(":")
        assert 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59
    except Exception:
        raise HTTPException(400, "schedule_time must be HH:MM")
    body.reit_tickers = [t.strip().upper() for t in body.reit_tickers if t.strip()]
    await db.settings.update_one({"_id": "singleton"}, {"$set": body.model_dump()}, upsert=True)
    _reschedule(body)
    return body.model_dump()


@api.get("/settings/models")
async def models_catalog():
    return AVAILABLE_MODELS


# ------------------------- scheduler -------------------------
async def _scheduled_run():
    settings = await pipeline.get_settings(db)
    if not settings.schedule_enabled:
        return
    if pipeline.RUN_LOCK.locked():
        logger.info("scheduled run skipped — already running")
        return
    run_id = await pipeline.create_run(db, trigger="scheduled")
    asyncio.create_task(pipeline.run_pipeline(db, run_id))
    logger.info(f"scheduled run started: {run_id}")


def _reschedule(settings: SettingsModel):
    try:
        scheduler.remove_all_jobs()
        hh, mm = settings.schedule_time.split(":")
        scheduler.add_job(_scheduled_run, CronTrigger(hour=int(hh), minute=int(mm),
                                                      timezone=ZoneInfo("Asia/Manila")),
                          id="daily_run")
        logger.info(f"scheduler set for {settings.schedule_time} Asia/Manila (enabled={settings.schedule_enabled})")
    except Exception as e:
        logger.error(f"failed to schedule: {e}")


@app.on_event("startup")
async def startup():
    settings = await pipeline.get_settings(db)
    _reschedule(settings)
    scheduler.start()
    # mark any zombie 'running' runs as failed (server restarted mid-run)
    await db.runs.update_many({"status": "running"},
                              {"$set": {"status": "failed", "error": "Interrupted by server restart",
                                        "finished_at": now_iso()}})


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown(wait=False)
    client.close()


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
