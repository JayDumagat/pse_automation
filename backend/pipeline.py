"""Daily pipeline orchestrator.
Stages: fetch -> validate -> compute -> store -> graphics -> captions -> qa -> ready
Critical stages (fetch/validate/compute/store) fail the run; graphics failures degrade
gracefully with warnings. Captions are created as manual editable fields.
"""
import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timezone

import httpx

import compute as compute_mod
import graphics_templates
import renderer
import sources
from models import GRAPHIC_TYPES, PLATFORMS, STAGES, SettingsModel

logger = logging.getLogger("pipeline")

RUN_LOCK = asyncio.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def notify(db, severity: str, title: str, message: str, run_id: str | None = None):
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "severity": severity, "title": title,
        "message": message, "run_id": run_id, "read": False, "created_at": now_iso(),
    })


async def get_settings(db) -> SettingsModel:
    doc = await db.settings.find_one({"_id": "singleton"}) or {}
    doc.pop("_id", None)
    return SettingsModel(**doc)


async def _update_stage(db, run_id: str, stage: str, status: str, error: str | None = None, meta: dict | None = None):
    run = await db.runs.find_one({"id": run_id}, {"_id": 0})
    stages = run["stages"]
    for st in stages:
        if st["name"] == stage:
            if status == "running":
                st["started_at"] = now_iso()
            else:
                st["ended_at"] = now_iso()
                if st.get("started_at"):
                    dur = (datetime.fromisoformat(st["ended_at"]) - datetime.fromisoformat(st["started_at"])).total_seconds()
                    st["duration_seconds"] = round(dur, 2)
            st["status"] = status
            st["error"] = error
            if meta:
                st["meta"] = meta
            break
    await db.runs.update_one({"id": run_id}, {"$set": {"stages": stages, "current_stage": stage}})


async def create_run(db, trigger: str) -> str:
    run_id = str(uuid.uuid4())
    await db.runs.insert_one({
        "id": run_id,
        "trigger": trigger,
        "status": "running",
        "current_stage": "fetch",
        "started_at": now_iso(),
        "finished_at": None,
        "duration_seconds": None,
        "market_date": None,
        "qa_flags": [],
        "error": None,
        "stages": [{"name": s, "status": "pending", "started_at": None, "ended_at": None,
                    "duration_seconds": None, "error": None, "meta": {}} for s in STAGES],
    })
    return run_id


async def run_pipeline(db, run_id: str):
    """Execute all stages for an existing run doc."""
    async with RUN_LOCK:
        settings = await get_settings(db)
        warnings: list[str] = []
        snapshot = None
        dividends: list[dict] = []
        tradingview_metrics: dict[str, dict] = {}
        board_lots: dict[str, int] = {}
        graphics_meta: list[dict] = []
        captions_docs: list[dict] = []
        try:
            await notify(db, "info", "Pipeline started", f"Run triggered — fetching PSE market data.", run_id)

            # ---- fetch ----
            await _update_stage(db, run_id, "fetch", "running")
            async with httpx.AsyncClient(follow_redirects=True) as client:
                quotes, quote_as_of = await sources.fetch_quotes(client)
                overview = await sources.fetch_market_overview(client)
                indices = overview["indices"]
                index_source = overview["source"]
                as_of = overview.get("as_of") or quote_as_of
                psei_symbols = {
                    compute_mod._normalise_symbol(symbol) for symbol in settings.psei_tickers
                }
                active_candidates = [
                    q.symbol for q in sorted(
                        (q for q in quotes if compute_mod._normalise_symbol(q.symbol) in psei_symbols and q.volume > 0),
                        key=lambda q: -q.value_traded,
                    )[:3]
                ]
                try:
                    tradingview_metrics = await sources.fetch_tradingview_stock_metrics(
                        client, list(dict.fromkeys([*settings.reit_tickers, *settings.divy_tickers])),
                    )
                except Exception as te:
                    warnings.append(f"TradingView dividend metrics unavailable: {te}")
                try:
                    board_lots = await sources.fetch_board_lots(
                        client, list(dict.fromkeys([*settings.reit_tickers, *settings.divy_tickers])),
                    )
                except Exception as be:
                    warnings.append(f"PSE Edge Board Lot data unavailable: {be}")
                try:
                    trade_counts = await sources.fetch_investagram_trade_counts(active_candidates)
                    for quote in quotes:
                        symbol = compute_mod._normalise_symbol(quote.symbol)
                        if symbol in trade_counts:
                            quote.trades = trade_counts[symbol]
                except Exception as ie:
                    warnings.append(f"Investagrams trade counts unavailable: {ie}")
                dividend_targets = list(dict.fromkeys(
                    [*settings.reit_tickers, *settings.divy_tickers]
                ))
                try:
                    edge_items = await sources.fetch_dividends(
                        client, days_back=365, detail_limit=64, target_symbols=dividend_targets,
                    )
                    history_items = await sources.fetch_dividend_history(client, dividend_targets, as_of)
                    combined = edge_items + history_items
                    unique = {}
                    for item in combined:
                        key = (
                            item.symbol.upper(), item.ex_date or item.disclosure_date,
                            item.dividend_per_share if item.dividend_per_share is not None else item.rate,
                        )
                        unique[key] = item
                    dividends = [item.model_dump() for item in unique.values()]
                except Exception as de:
                    warnings.append(f"Dividend source unavailable: {de}")
                    dividends = []
            await _update_stage(db, run_id, "fetch", "success", meta={
                "quotes": len(quotes), "indices": len(indices),
                "index_source": index_source, "dividends": len(dividends),
                "market_as_of": as_of.isoformat(),
                "tradingview_yields": sum(1 for x in tradingview_metrics.values() if x.get("yield_ttm") is not None),
                "board_lots": len(board_lots),
                "investagrams_trade_counts": sum(1 for q in quotes if q.trades is not None),
                "official_market_stats": bool(overview.get("stats")),
            })

            # ---- validate ----
            await _update_stage(db, run_id, "validate", "running")
            # Pydantic already validated at parse; assert structural invariants here
            assert len(quotes) >= 100, f"too few quotes: {len(quotes)}"
            assert indices["PSEi"].value > 500, "PSEi value implausible"
            sector_count = sum(1 for n in sources.SECTOR_NAMES if n in indices)
            await _update_stage(db, run_id, "validate", "success", meta={"sectors_present": sector_count})

            # ---- compute ----
            await _update_stage(db, run_id, "compute", "running")
            snapshot = compute_mod.compute_snapshot(
                quotes, indices, as_of, settings.reit_tickers, settings.divy_tickers,
                settings.psei_tickers, overview.get("stats"), dividends,
                tradingview_metrics=tradingview_metrics, board_lots=board_lots,
            )
            snapshot["market_data_source"] = overview["source"]
            snapshot["market_totals_source"] = "pse-edge" if overview.get("stats") else "derived"
            await _update_stage(db, run_id, "compute", "success", meta={
                "gainers": len(snapshot["gainers"]), "losers": len(snapshot["losers"]),
                "actives": len(snapshot["actives"]), "psei_stocks": len(snapshot["psei_stocks"]),
                "reits": len(snapshot["reit_metrics"]), "divy": len(snapshot["divy_metrics"]),
            })

            # ---- store ----
            await _update_stage(db, run_id, "store", "running")
            market_date = snapshot["summary"]["market_date"]
            snap_doc = {
                "id": str(uuid.uuid4()), "run_id": run_id, "market_date": market_date,
                **snapshot, "dividends": dividends, "created_at": now_iso(),
            }
            await db.snapshots.insert_one(dict(snap_doc))
            await db.runs.update_one({"id": run_id}, {"$set": {"market_date": market_date}})
            await _update_stage(db, run_id, "store", "success")

            # ---- graphics (non-critical) ----
            await _update_stage(db, run_id, "graphics", "running")
            try:
                html_map = graphics_templates.build_all(snapshot, dividends, settings.brand_name)
                graphics_meta = await renderer.render_graphics(run_id, html_map)
                for g in graphics_meta:
                    await db.graphics.insert_one({**g, "id": str(uuid.uuid4()), "created_at": now_iso()})
                status = "success" if len(graphics_meta) == len(GRAPHIC_TYPES) else "warning"
                await _update_stage(db, run_id, "graphics", status, meta={"generated": len(graphics_meta)})
                if len(graphics_meta) < len(GRAPHIC_TYPES):
                    warnings.append(f"Only {len(graphics_meta)}/{len(GRAPHIC_TYPES)} graphics generated")
            except Exception as ge:
                warnings.append(f"Graphics generation failed: {ge}")
                await _update_stage(db, run_id, "graphics", "failed", error=str(ge))

            # ---- captions (manual) ----
            await _update_stage(db, run_id, "captions", "running")
            for platform in PLATFORMS:
                doc = {
                    "id": str(uuid.uuid4()), "run_id": run_id, "platform": platform,
                    "text": "", "provider": "manual", "model": "manual",
                    "edited": False, "updated_at": now_iso(),
                }
                captions_docs.append(doc)
                await db.captions.insert_one(dict(doc))
            await _update_stage(db, run_id, "captions", "success", meta={
                "mode": "manual", "platforms": len(captions_docs),
            })

            # ---- qa ----
            await _update_stage(db, run_id, "qa", "running")
            flags = compute_mod.qa_checks(snapshot, graphics_meta, captions_docs)
            for w in warnings:
                flags.append({"severity": "warning", "check": "stage_warning", "message": w})
            await db.runs.update_one({"id": run_id}, {"$set": {"qa_flags": flags}})
            qa_status = "success" if not any(f["severity"] == "error" for f in flags) else "warning"
            await _update_stage(db, run_id, "qa", qa_status, meta={"flags": len(flags)})
            if flags:
                await notify(db, "warning", "QA flags raised",
                             f"{len(flags)} QA flag(s) on run — review before publishing.", run_id)

            # ---- ready ----
            await _update_stage(db, run_id, "ready", "running")
            for platform in PLATFORMS:
                await db.publishing.insert_one({
                    "id": str(uuid.uuid4()), "run_id": run_id, "platform": platform,
                    "status": "pending", "note": "", "updated_at": now_iso(),
                })
            await _update_stage(db, run_id, "ready", "success")

            finished = now_iso()
            run = await db.runs.find_one({"id": run_id}, {"_id": 0})
            dur = (datetime.fromisoformat(finished) - datetime.fromisoformat(run["started_at"])).total_seconds()
            final_status = "ready" if not warnings else "ready_with_warnings"
            await db.runs.update_one({"id": run_id}, {"$set": {
                "status": final_status, "finished_at": finished, "duration_seconds": round(dur, 1),
                "current_stage": "ready",
            }})
            await notify(db, "success", "Run completed",
                         f"Pipeline finished in {round(dur, 1)}s — {len(graphics_meta)} graphics, "
                         f"{len(captions_docs)} captions ready for review.", run_id)
        except Exception as e:
            logger.error(f"pipeline failed: {e}\n{traceback.format_exc()}")
            finished = now_iso()
            run = await db.runs.find_one({"id": run_id}, {"_id": 0})
            dur = (datetime.fromisoformat(finished) - datetime.fromisoformat(run["started_at"])).total_seconds()
            current = run.get("current_stage", "fetch")
            await _update_stage(db, run_id, current, "failed", error=str(e))
            await db.runs.update_one({"id": run_id}, {"$set": {
                "status": "failed", "finished_at": finished,
                "duration_seconds": round(dur, 1), "error": str(e),
            }})
            await notify(db, "error", "Run failed", f"Stage '{current}' failed: {e}", run_id)


async def regenerate_graphics(db, run_id: str) -> int:
    settings = await get_settings(db)
    snap = await db.snapshots.find_one({"run_id": run_id}, {"_id": 0})
    if not snap:
        raise ValueError("No snapshot for this run")
    html_map = graphics_templates.build_all(snap, snap.get("dividends", []), settings.brand_name)
    graphics_meta = await renderer.render_graphics(run_id, html_map)
    await db.graphics.delete_many({"run_id": run_id})
    for g in graphics_meta:
        await db.graphics.insert_one({**g, "id": str(uuid.uuid4()), "created_at": now_iso()})
    await notify(db, "info", "Graphics regenerated", f"{len(graphics_meta)} graphics re-rendered.", run_id)
    return len(graphics_meta)


async def regenerate_all_captions(db, run_id: str) -> int:
    raise ValueError("Automatic captions are disabled. Enter and save captions manually.")
