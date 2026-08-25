"""Deterministic financial computations and completeness checks.  No LLM math."""
from datetime import date, datetime, timedelta
from typing import Any

from models import (
    DIVY_TICKERS, PSEI_MEMBERSHIP_AS_OF, PSEI_TICKERS, REIT_TICKERS,
    IndexQuote, MarketSummary, StockQuote,
)


INDEX_BOARD_ORDER = [
    "PSEi", "PSEi Total Return", "All Shares", "PSE DivY", "PSE MidCap",
    "Financials", "Industrial", "Holding Firms", "Property", "Services", "Mining & Oil",
]

SECTOR_BOARD_ORDER = [
    "Financials", "Industrial", "Holding Firms", "Property", "Services", "Mining & Oil",
]


def _normalise_symbol(value: str) -> str:
    value = (value or "").strip().upper()
    return {"MERIT": "MER"}.get(value, value)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    clean = value.strip().replace(".", "")
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    return None


def _dividend_totals(dividends: list[dict] | None, as_of: datetime) -> dict[str, float]:
    """Sum unique cash distributions during the trailing 365-day window."""
    totals: dict[str, float] = {}
    seen: set[tuple[str, str, float]] = set()
    cutoff = as_of.date() - timedelta(days=365)
    for item in dividends or []:
        symbol = _normalise_symbol(str(item.get("symbol") or ""))
        if not symbol:
            continue
        raw_amount = item.get("dividend_per_share")
        if raw_amount is None:
            try:
                raw_amount = float(str(item.get("rate") or "").replace(",", ""))
            except ValueError:
                raw_amount = None
        else:
            try:
                raw_amount = float(raw_amount)
            except (TypeError, ValueError):
                raw_amount = None
        event_date = _parse_date(item.get("ex_date") or item.get("disclosure_date"))
        if raw_amount is None or raw_amount <= 0 or event_date is None:
            continue
        if not cutoff <= event_date <= as_of.date():
            continue
        key = (symbol, event_date.isoformat(), round(float(raw_amount), 8))
        if key in seen:
            continue
        seen.add(key)
        totals[symbol] = round(totals.get(symbol, 0.0) + float(raw_amount), 8)
    return totals


def _quote_metric(
    ticker: str,
    quote: StockQuote | None,
    dividend_totals: dict[str, float],
    tradingview_metrics: dict[str, dict] | None = None,
    board_lots: dict[str, int] | None = None,
) -> dict[str, Any]:
    symbol = _normalise_symbol(ticker)
    tv_metric = (tradingview_metrics or {}).get(symbol, {})
    lot = (board_lots or {}).get(symbol)
    if quote is None:
        return {
            "ticker": symbol, "symbol": symbol, "name": "", "price": None,
            "percent_change": None, "value_traded": None, "value_turnover": None,
            "trades": None, "dividend_per_share_ttm": None, "yield_ttm": None,
            "yield_source": None, "board_lot": lot,
            "board_lot_source": "pse-edge" if lot is not None else None,
            "minimum_investment": None, "data_status": "missing_quote",
        }
    tv_dps = tv_metric.get("dividend_per_share_ttm")
    dps = tv_dps if tv_dps is not None else dividend_totals.get(symbol)
    minimum = round(quote.price * lot, 2) if lot else None
    tv_yield = tv_metric.get("yield_ttm")
    # TradingView's public dividends page always exposes the TTM yield, while
    # its scanner may omit the matching DPS field. Reconstruct the TTM
    # dividend/share from those two values rather than leaving the metric blank.
    if dps is None and tv_yield is not None and quote.price > 0:
        dps = round(quote.price * float(tv_yield) / 100, 8)
    if tv_yield is not None:
        yield_ttm = round(float(tv_yield), 2)
        yield_source = "tradingview"
    else:
        yield_ttm = round(dps / quote.price * 100, 2) if dps is not None and quote.price > 0 else None
        yield_source = "derived" if yield_ttm is not None else None
    return {
        "ticker": symbol, "symbol": symbol, "name": quote.name, "price": quote.price,
        "percent_change": quote.percent_change, "volume": quote.volume,
        "value_traded": quote.value_traded, "value_turnover": quote.value_traded,
        "trades": quote.trades, "dividend_per_share_ttm": dps, "yield_ttm": yield_ttm,
        "yield_source": yield_source, "board_lot": lot,
        "board_lot_source": "pse-edge" if lot is not None else None,
        "minimum_investment": minimum, "data_status": "ok",
    }


def _explanation(summary: dict, sectors: list[dict], gainers: list[dict], losers: list[dict], actives: list[dict]) -> str:
    direction = "rose" if summary["change_points"] > 0 else "fell" if summary["change_points"] < 0 else "finished flat"
    breadth = f"{summary['advancers']} advancers, {summary['decliners']} decliners, and {summary['unchanged']} unchanged"
    sector_text = ""
    if sectors:
        strongest = max(sectors, key=lambda row: row["change_percent"])
        weakest = min(sectors, key=lambda row: row["change_percent"])
        sector_text = f" {strongest['name']} led the sectors at {strongest['change_percent']:+.2f}%, while {weakest['name']} was the weakest at {weakest['change_percent']:+.2f}%."
    movers_text = ""
    if gainers:
        movers_text += f" The leading PSEi gainer was {gainers[0]['symbol']} ({gainers[0]['percent_change']:+.2f}%)."
    if losers:
        movers_text += f" The weakest was {losers[0]['symbol']} ({losers[0]['percent_change']:+.2f}%)."
    trades_text = (
        f" The market recorded {summary['total_trades']:,} trades."
        if summary.get("total_trades") is not None else
        " Per-stock trade counts were not published by the available quote feed."
    )
    return (
        f"The PSEi {direction} {abs(summary['change_points']):,.2f} points ({summary['change_percent']:+.2f}%) "
        f"to {summary['psei_value']:,.2f}. Market breadth was {breadth}; value turnover reached "
        f"₱{summary['approx_value_turnover']:,.0f}.{trades_text}{sector_text}{movers_text}"
    )


def compute_snapshot(
    quotes: list[StockQuote],
    indices: dict[str, IndexQuote],
    as_of: datetime,
    reit_tickers: list[str] | None = None,
    divy_tickers: list[str] | None = None,
    psei_tickers: list[str] | None = None,
    market_stats: dict | None = None,
    dividends: list[dict] | None = None,
    tradingview_metrics: dict[str, dict] | None = None,
    board_lots: dict[str, int] | None = None,
) -> dict:
    """Build the complete daily snapshot from quote, index, and market-total inputs."""
    psei = indices["PSEi"]
    stats = market_stats or {}
    quote_map = {_normalise_symbol(q.symbol): q for q in quotes}
    psei_universe = [_normalise_symbol(t) for t in (psei_tickers or PSEI_TICKERS)]
    psei_quotes = [quote_map[t] for t in psei_universe if t in quote_map]
    traded_psei = [q for q in psei_quotes if q.volume > 0]

    derived_advancers = sum(1 for q in quotes if q.percent_change > 0)
    derived_decliners = sum(1 for q in quotes if q.percent_change < 0)
    derived_unchanged = sum(1 for q in quotes if q.percent_change == 0)
    derived_volume = sum(q.volume for q in quotes)
    derived_turnover = round(sum(q.value_traded for q in quotes), 2)
    advancers = int(stats.get("advances", derived_advancers))
    decliners = int(stats.get("declines", derived_decliners))
    unchanged = int(stats.get("unchanged", derived_unchanged))
    total_volume = int(stats.get("total volume", derived_volume))
    total_trades = stats.get("total trades")
    total_trades = int(total_trades) if total_trades is not None else None
    turnover = round(float(stats.get("total value", derived_turnover)), 2)
    total_quotes = advancers + decliners + unchanged

    def row(q: StockQuote) -> dict:
        item = q.model_dump()
        item["ticker"] = q.symbol
        item["value_turnover"] = q.value_traded
        return item

    gainers = [row(q) for q in sorted(
        [q for q in traded_psei if q.percent_change > 0], key=lambda q: -q.percent_change,
    )[:3]]
    losers = [row(q) for q in sorted(
        [q for q in traded_psei if q.percent_change < 0], key=lambda q: q.percent_change,
    )[:3]]
    actives = [row(q) for q in sorted(traded_psei, key=lambda q: -q.value_traded)[:3]]
    psei_stocks = [row(quote_map[t]) if t in quote_map else {
        "ticker": t, "symbol": t, "name": "", "price": None, "percent_change": None,
        "volume": None, "value_traded": None, "value_turnover": None, "trades": None,
        "data_status": "missing_quote",
    } for t in psei_universe]

    reit_tickers = [_normalise_symbol(t) for t in (reit_tickers or REIT_TICKERS)]
    divy_tickers = [_normalise_symbol(t) for t in (divy_tickers or DIVY_TICKERS)]
    dividend_totals = _dividend_totals(dividends, as_of)
    reit_metrics = [
        _quote_metric(t, quote_map.get(t), dividend_totals, tradingview_metrics, board_lots)
        for t in reit_tickers
    ]
    divy_metrics = [
        _quote_metric(t, quote_map.get(t), dividend_totals, tradingview_metrics, board_lots)
        for t in divy_tickers
    ]
    # The boards are daily movers first. Positive changes naturally lead;
    # unchanged and negative rows follow in descending order.
    change_sort = lambda item: (item["percent_change"] is None, -(item["percent_change"] or 0), item["ticker"])
    reit_metrics.sort(key=change_sort)
    divy_metrics.sort(key=change_sort)

    summary = MarketSummary(
        market_date=as_of.date().isoformat(), psei_value=psei.value,
        change_points=psei.change_points, change_percent=psei.change_percent,
        approx_value_turnover=turnover, value_turnover=turnover,
        advancers=advancers, decliners=decliners,
        unchanged=unchanged, total_quotes=total_quotes, total_volume=total_volume,
        total_trades=total_trades, value_turnover_source="pse-edge" if market_stats and "total value" in stats else "derived",
    ).model_dump()
    index_board = [indices[n].model_dump() for n in INDEX_BOARD_ORDER if n in indices]
    sectors = [indices[n].model_dump() for n in SECTOR_BOARD_ORDER if n in indices]
    explanation = _explanation(summary, sectors, gainers, losers, actives)
    missing_psei = [t for t in psei_universe if t not in quote_map]
    return {
        "summary": summary,
        "indices": {k: v.model_dump() for k, v in indices.items()},
        "index_board": index_board,
        "sectors": sectors,
        "gainers": gainers,
        "losers": losers,
        "actives": actives,
        "psei_stocks": psei_stocks,
        # Keep the original lightweight key for existing graphics/API clients.
        "reits": [quote_map[t].model_dump() for t in reit_tickers if t in quote_map],
        "reit_metrics": reit_metrics,
        "divy_metrics": divy_metrics,
        "explanation": explanation,
        "as_of": as_of.isoformat(),
        "data_completeness": {
            "psei_membership_as_of": PSEI_MEMBERSHIP_AS_OF,
            "psei_expected": len(psei_universe), "psei_found": len(psei_quotes),
            "psei_missing": missing_psei,
            "reits_expected": len(reit_tickers), "reits_found": sum(1 for x in reit_metrics if x["data_status"] == "ok"),
            "divy_expected": len(divy_tickers), "divy_found": sum(1 for x in divy_metrics if x["data_status"] == "ok"),
            "reit_board_lots_found": sum(1 for x in reit_metrics if x.get("board_lot") is not None),
            "divy_board_lots_found": sum(1 for x in divy_metrics if x.get("board_lot") is not None),
            "tradingview_yields_found": sum(
                1 for x in reit_metrics + divy_metrics if x.get("yield_source") == "tradingview"
            ),
            "psei_trade_counts_found": sum(1 for q in psei_quotes if q.trades is not None),
        },
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
        flag("warning", "turnover", "Value turnover is zero — market may be closed or the source failed")
    extremes = [q for q in snapshot["gainers"] + snapshot["losers"] if abs(q["percent_change"]) > 60]
    if extremes:
        flag("warning", "extreme_moves", f"{len(extremes)} quote(s) with |change| > 60%: " + ", ".join(q["symbol"] for q in extremes))
    completeness = snapshot.get("data_completeness", {})
    if completeness.get("psei_missing"):
        flag("warning", "psei_constituents", "Missing PSEi constituent quotes: " + ", ".join(completeness["psei_missing"]))
    for key, label in (("reit_metrics", "REIT"), ("divy_metrics", "DivY")):
        rows = snapshot.get(key, [])
        missing_prices = [row["ticker"] for row in rows if row.get("price") is None]
        missing_yields = [row["ticker"] for row in rows if row.get("yield_ttm") is None]
        fallback_yields = [
            row["ticker"] for row in rows
            if row.get("yield_ttm") is not None and row.get("yield_source") != "tradingview"
        ]
        missing_lots = [row["ticker"] for row in rows if row.get("board_lot") is None]
        if missing_prices:
            flag("warning", f"{key}_prices", f"Missing {label} prices: " + ", ".join(missing_prices))
        if missing_yields:
            flag("warning", f"{key}_ttm", f"Missing {label} TTM dividend data: " + ", ".join(missing_yields))
        if fallback_yields:
            flag("warning", f"{key}_yield_source", f"{label} TTM yield fell back to a derived value for: " + ", ".join(fallback_yields))
        if missing_lots:
            flag("warning", f"{key}_board_lot", f"Missing PSE Edge Board Lot: " + ", ".join(missing_lots))
    if any(q.get("trades") is None for q in snapshot.get("actives", [])):
        flag("warning", "per_stock_trades", "Some PSEi per-stock trade counts were not available from the Investagrams Historical Data tab.")
    if len(graphics) < 5:
        flag("warning", "graphics_count", f"Only {len(graphics)}/5 graphics were generated")
    for g in graphics:
        if g.get("size_bytes", 0) < 20000:
            flag("warning", "graphic_size", f"Graphic {g['type']} looks too small ({g.get('size_bytes', 0)} bytes)")
    have = {c["platform"] for c in captions if (c.get("text") or "").strip()}
    missing = [p for p in ["instagram", "facebook", "linkedin", "x"] if p not in have]
    if missing:
        if captions and all(c.get("provider") == "manual" for c in captions):
            flag("info", "captions_manual", "Captions are manual input and are still blank for: " + ", ".join(missing))
        else:
            flag("warning", "captions_missing", "Missing captions for: " + ", ".join(missing))
    return flags
