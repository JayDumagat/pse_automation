"""Deterministic financial computations + QA validation. NO LLM math here."""
from datetime import datetime

from models import IndexQuote, MarketSummary, StockQuote


def compute_snapshot(quotes: list[StockQuote], indices: dict[str, IndexQuote],
                     as_of: datetime, reit_tickers: list[str]) -> dict:
    psei = indices["PSEi"]
    traded = [q for q in quotes if q.volume > 0]
    advancers = sum(1 for q in quotes if q.percent_change > 0)
    decliners = sum(1 for q in quotes if q.percent_change < 0)
    unchanged = sum(1 for q in quotes if q.percent_change == 0)
    turnover = round(sum(q.value_traded for q in quotes), 2)

    gainers = sorted([q for q in traded if q.percent_change > 0], key=lambda q: -q.percent_change)[:10]
    losers = sorted([q for q in traded if q.percent_change < 0], key=lambda q: q.percent_change)[:10]
    actives = sorted(traded, key=lambda q: -q.value_traded)[:10]
    reit_set = {t.upper() for t in reit_tickers}
    reits = sorted([q for q in quotes if q.symbol.upper() in reit_set], key=lambda q: q.symbol)

    summary = MarketSummary(
        market_date=as_of.date().isoformat(),
        psei_value=psei.value, change_points=psei.change_points,
        change_percent=psei.change_percent, approx_value_turnover=turnover,
        advancers=advancers, decliners=decliners, unchanged=unchanged,
        total_quotes=len(quotes),
    )
    sectors = [indices[n].model_dump() for n in
               ["Financials", "Industrial", "Holding Firms", "Property", "Services", "Mining & Oil"]
               if n in indices]
    return {
        "summary": summary.model_dump(),
        "indices": {k: v.model_dump() for k, v in indices.items()},
        "sectors": sectors,
        "gainers": [q.model_dump() for q in gainers],
        "losers": [q.model_dump() for q in losers],
        "actives": [q.model_dump() for q in actives],
        "reits": [q.model_dump() for q in reits],
        "as_of": as_of.isoformat(),
    }


def qa_checks(snapshot: dict, graphics: list[dict], captions: list[dict]) -> list[dict]:
    """Deterministic sanity checks. Returns list of {severity, check, message}."""
    flags = []
    s = snapshot["summary"]

    def flag(severity, check, message):
        flags.append({"severity": severity, "check": check, "message": message})

    if s["advancers"] + s["decliners"] + s["unchanged"] != s["total_quotes"]:
        flag("error", "breadth_sum", "Advancers + decliners + unchanged does not equal total quotes")
    if abs(s["change_percent"]) > 15:
        flag("warning", "psei_move", f"PSEi moved {s['change_percent']:+.2f}% — unusually large, verify source")
    if s["approx_value_turnover"] <= 0:
        flag("warning", "turnover", "Approximate value turnover is zero — market may be closed")
    extremes = [q for q in snapshot["gainers"] + snapshot["losers"] if abs(q["percent_change"]) > 60]
    if extremes:
        flag("warning", "extreme_moves", f"{len(extremes)} quote(s) with |change| > 60%: " + ", ".join(q["symbol"] for q in extremes))
    if len(snapshot["reits"]) < 3:
        flag("warning", "reits_count", f"Only {len(snapshot['reits'])} REITs matched the configured ticker list")
    if len(graphics) < 5:
        flag("warning", "graphics_count", f"Only {len(graphics)}/5 graphics were generated")
    for g in graphics:
        if g.get("size_bytes", 0) < 20000:
            flag("warning", "graphic_size", f"Graphic {g['type']} looks too small ({g.get('size_bytes', 0)} bytes)")
    have = {c["platform"] for c in captions if (c.get("text") or "").strip()}
    missing = [p for p in ["instagram", "facebook", "linkedin", "x"] if p not in have]
    if missing:
        flag("warning", "captions_missing", "Missing captions for: " + ", ".join(missing))
    return flags
