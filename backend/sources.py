"""Market data sources — resilient fetchers with explicit source fallbacks."""
import asyncio
import logging
import re
from datetime import date, datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from models import DIVY_TICKERS, DividendItem, IndexQuote, StockQuote

logger = logging.getLogger("sources")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

PHISIX_URLS = [
    "http://phisix-api3.appspot.com/stocks.json",
    "https://phisix-api4.appspot.com/stocks.json",
]

TV_INDEX_TICKERS = {
    "PSE:PSEI": "PSEi",
    "PSE:ALL": "All Shares",
    "PSE:FIN": "Financials",
    "PSE:IND": "Industrial",
    "PSE:HDG": "Holding Firms",
    "PSE:PRO": "Property",
    "PSE:SVC": "Services",
    "PSE:M_O": "Mining & Oil",
}

YAHOO_TICKERS = {
    "PSEI.PS": "PSEi", "ALL.PS": "All Shares", "FIN.PS": "Financials",
    "IND.PS": "Industrial", "HDG.PS": "Holding Firms", "PRO.PS": "Property",
    "SVC.PS": "Services", "M-O.PS": "Mining & Oil",
}

SECTOR_NAMES = ["Financials", "Industrial", "Holding Firms", "Property", "Services", "Mining & Oil"]

PSE_INDEX_SUMMARY_URL = "https://edge.pse.com.ph/index/form.do"
PSE_INDEX_NAMES = {
    "psei": "PSEi",
    "all shares": "All Shares",
    "financials": "Financials",
    "industrial": "Industrial",
    "holding firms": "Holding Firms",
    "property": "Property",
    "services": "Services",
    "mining and oil": "Mining & Oil",
    "mining & oil": "Mining & Oil",
}


def _first_number(value: str, signed: bool = True) -> float | None:
    """Read the first number from PSE display text, including arrow direction."""
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", value or "")
    if not match:
        return None
    number = float(match.group(0).replace(",", ""))
    if signed and ("▼" in value or "down" in value.lower()):
        number = -abs(number)
    return number


def _parse_pse_index_summary(html: str) -> tuple[dict[str, IndexQuote], dict, datetime | None]:
    """Parse the public PSE Edge index summary and market totals."""
    soup = BeautifulSoup(html, "html.parser")
    indices: dict[str, IndexQuote] = {}
    stats: dict[str, int | float] = {}
    for row in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
        if len(cells) < 2:
            continue
        label = re.sub(r"\s+", " ", cells[0]).strip()
        normalized = label.lower().replace("  ", " ")
        index_name = PSE_INDEX_NAMES.get(normalized)
        if index_name and len(cells) >= 4:
            value = _first_number(cells[1], signed=False)
            change = _first_number(cells[2])
            percent = _first_number(cells[3])
            if value is None or change is None or percent is None:
                continue
            # Some PSE templates put the direction only on %Chg. Carry it to
            # points too, because the points cell is visually unsigned.
            if ("▼" in cells[3] or "-" in cells[3]) and change > 0:
                change = -change
            indices[index_name] = IndexQuote(
                symbol=index_name.upper().replace(" ", "_"), name=index_name,
                value=round(value, 2), previous_close=round(value - change, 2),
                change_points=round(change, 2), change_percent=round(percent, 2),
            )
            continue
        stat_label = normalized.rstrip(":")
        if stat_label in {"total volume", "total trades", "total value", "advances", "declines", "unchanged"}:
            number = _first_number(" ".join(cells[1:]), signed=False)
            if number is not None:
                stats[stat_label] = int(number)

    page_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    as_of = None
    match = re.search(
        r"As of\s+([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})(?:\s+(\d{1,2}:\d{2}\s*[AP]M))?",
        page_text, re.I,
    )
    if match:
        for fmt in ("%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p", "%b %d, %Y", "%B %d, %Y"):
            try:
                raw = f"{match.group(1)} {match.group(2)}" if match.group(2) else match.group(1)
                as_of = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
    if "PSEi" not in indices:
        raise ValueError("PSE Edge index summary did not contain PSEi")
    return indices, stats, as_of


async def fetch_quotes(client: httpx.AsyncClient) -> tuple[list[StockQuote], datetime]:
    """All PSE stock quotes via Phisix."""
    last_err = None
    for url in PHISIX_URLS:
        for attempt in range(2):
            try:
                r = await client.get(url, timeout=25)
                r.raise_for_status()
                data = r.json()
                quotes = []
                for s in data["stocks"]:
                    price = float(s["price"]["amount"])
                    volume = int(s.get("volume") or 0)
                    raw_trades = s.get("trades", s.get("tradeCount", s.get("numTrades")))
                    try:
                        trades = int(raw_trades) if raw_trades is not None else None
                    except (TypeError, ValueError):
                        trades = None
                    quotes.append(StockQuote(
                        symbol=s["symbol"], name=s["name"], price=price,
                        percent_change=float(s.get("percentChange") or 0),
                        volume=volume, value_traded=round(price * volume, 2), trades=trades,
                    ))
                as_of = datetime.fromisoformat(data["as_of"])
                if len(quotes) < 100:
                    raise ValueError(f"suspiciously few quotes: {len(quotes)}")
                return quotes, as_of
            except Exception as e:
                last_err = e
                logger.warning(f"phisix {url} attempt {attempt+1} failed: {e}")
                await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"All quote sources failed: {last_err}")


async def fetch_indices(client: httpx.AsyncClient) -> tuple[dict[str, IndexQuote], str]:
    """PSEi + sector indices. TradingView primary, Yahoo fallback."""
    try:
        return await _fetch_indices_tradingview(client), "tradingview"
    except Exception as e:
        logger.warning(f"TradingView indices failed, falling back to Yahoo: {e}")
        return await _fetch_indices_yahoo(client), "yahoo"


async def fetch_market_overview(client: httpx.AsyncClient) -> dict:
    """Fetch official PSE index values, market totals, and official breadth."""
    try:
        response = await client.get(PSE_INDEX_SUMMARY_URL, timeout=30, headers={"User-Agent": UA})
        response.raise_for_status()
        indices, stats, as_of = _parse_pse_index_summary(response.text)
        return {"indices": indices, "stats": stats, "as_of": as_of, "source": "pse-edge"}
    except Exception as e:
        logger.warning(f"PSE Edge market summary failed, falling back to index feeds: {e}")
        indices, source = await fetch_indices(client)
        return {"indices": indices, "stats": {}, "as_of": None, "source": source}


async def _fetch_indices_tradingview(client: httpx.AsyncClient) -> dict[str, IndexQuote]:
    payload = {
        "symbols": {"tickers": list(TV_INDEX_TICKERS.keys()), "query": {"types": []}},
        "columns": ["name", "close", "change", "change_abs", "high", "low", "description"],
    }
    r = await client.post("https://scanner.tradingview.com/philippines/scan",
                          json=payload, timeout=25, headers={"User-Agent": UA})
    r.raise_for_status()
    out = {}
    for row in r.json()["data"]:
        name = TV_INDEX_TICKERS.get(row["s"])
        if not name:
            continue
        _, close, chg_pct, chg_abs, high, low, _d = row["d"]
        out[name] = IndexQuote(
            symbol=row["s"], name=name, value=round(float(close), 2),
            previous_close=round(float(close) - float(chg_abs), 2),
            change_points=round(float(chg_abs), 2), change_percent=round(float(chg_pct), 2),
            day_high=high, day_low=low,
        )
    if "PSEi" not in out:
        raise ValueError("PSEi missing from TradingView response")
    return out


async def _fetch_indices_yahoo(client: httpx.AsyncClient) -> dict[str, IndexQuote]:
    out = {}
    for ticker, name in YAHOO_TICKERS.items():
        last_err = None
        for attempt, host in enumerate(["query1", "query2"]):
            try:
                url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
                r = await client.get(url, timeout=20, headers={"User-Agent": UA})
                r.raise_for_status()
                meta = r.json()["chart"]["result"][0]["meta"]
                value = float(meta["regularMarketPrice"])
                prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or value)
                out[name] = IndexQuote(
                    symbol=ticker, name=name, value=round(value, 2), previous_close=round(prev, 2),
                    change_points=round(value - prev, 2),
                    change_percent=round((value - prev) / prev * 100, 2) if prev else 0.0,
                    day_high=meta.get("regularMarketDayHigh"), day_low=meta.get("regularMarketDayLow"),
                )
                break
            except Exception as e:
                last_err = e
                await asyncio.sleep(2.5 * (attempt + 1))
        else:
            logger.warning(f"Yahoo failed for {ticker}: {last_err}")
        await asyncio.sleep(1.2)
    if "PSEi" not in out:
        raise RuntimeError("Index data unavailable from all sources")
    return out


def _normalise_symbol(value: str) -> str:
    value = (value or "").strip().upper()
    return {"MERIT": "MER"}.get(value, value)


def _find_symbol(text: str, target_symbols: set[str] | None = None) -> str:
    candidates = re.findall(r"\b[A-Z][A-Z0-9]{1,5}\b", text.upper())
    if target_symbols:
        for candidate in candidates:
            if _normalise_symbol(candidate) in target_symbols:
                return _normalise_symbol(candidate)
        return ""
    return _normalise_symbol(candidates[0]) if candidates else ""


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    clean = re.sub(r"\s+", " ", value.strip().replace(".", ""))
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    return None


def _parse_dividend_rate(text: str) -> float | None:
    patterns = (
        r"Dividend\s+Rate\s*:?\s*(?:P(?:hp)?\.?\s*)?([\d,]+(?:\.\d+)?)",
        r"(?:Cash\s+)?Dividend\s*(?:per\s+share|/\s*share)\s*:?\s*(?:P(?:hp)?\.?\s*)?([\d,]+(?:\.\d+)?)",
        r"Rate\s*:?\s*(?:P(?:hp)?\.?\s*)?([\d,]+(?:\.\d+)?)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


async def fetch_dividends(
    client: httpx.AsyncClient,
    days_back: int = 365,
    detail_limit: int = 64,
    target_symbols: list[str] | None = None,
) -> list[DividendItem]:
    """Cash dividend declarations from PSE Edge, enriched for TTM metrics."""
    to_d = datetime.now()
    frm = to_d - timedelta(days=days_back)
    targets = {_normalise_symbol(s) for s in (target_symbols or DIVY_TICKERS)}
    url = ("https://edge.pse.com.ph/companyDisclosures/search.ax?keyword=&tmplNm=Declaration%20of%20Cash%20Dividends"
           f"&fromDate={frm.strftime('%m-%d-%Y')}&toDate={to_d.strftime('%m-%d-%Y')}"
           "&sortType=date&dateSortType=DESC&cmpySortType=ASC&pageNo=1")
    response = await client.get(
        url, timeout=30,
        headers={"User-Agent": UA, "Referer": "https://edge.pse.com.ph/announcements/form.do"},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    items: list[DividendItem] = []
    for row in soup.find_all("tr"):
        raw = str(row)
        match = re.search(r"openPopup\(['\"]([A-Za-z0-9_-]+)['\"]\)", raw, re.I)
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if not match or len(cells) < 2:
            continue
        title_match = re.search(r"openPopup\(['\"][^'\"]+['\"]\).*?>([^<]+)</a>", raw, re.S | re.I)
        title = title_match.group(1).strip() if title_match else (cells[0] or "Cash dividend declaration")
        row_text = " ".join(cells)
        symbol = _find_symbol(row_text, targets)
        if symbol and target_symbols and symbol not in targets:
            continue
        items.append(DividendItem(
            symbol=symbol, title=title, disclosure_date=cells[1], edge_no=match.group(1),
        ))

    sem = asyncio.Semaphore(4)

    async def enrich(item: DividendItem):
        async with sem:
            try:
                viewer = await client.get(
                    f"https://edge.pse.com.ph/openDiscViewer.do?edge_no={item.edge_no}",
                    timeout=25, headers={"User-Agent": UA},
                )
                file_id = re.search(r"downloadHtml\.do\?file_id=(\d+)", viewer.text)
                if not file_id:
                    return
                detail = await client.get(
                    f"https://edge.pse.com.ph/downloadHtml.do?file_id={file_id.group(1)}",
                    timeout=25, headers={"User-Agent": UA},
                )
                txt = re.sub(r"\s+", " ", BeautifulSoup(detail.text, "html.parser").get_text(" ", strip=True))
                if not item.symbol:
                    item.symbol = _find_symbol(txt, targets)
                company_match = re.search(
                    r"Exact name of (?:issuer|registrant) as specified in its charter\s+(.{3,100}?)\s+\d{1,2}\.\s",
                    txt, re.I,
                )
                item.company = company_match.group(1).strip() if company_match else item.company
                ex = re.search(r"Ex-?Date\s*:?\s*([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})", txt, re.I)
                rec = re.search(r"Record Date\s*:?\s*([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})", txt, re.I)
                pay = re.search(r"Payment Date\s*:?\s*([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})", txt, re.I)
                amount = _parse_dividend_rate(txt)
                item.ex_date = ex.group(1) if ex else None
                item.record_date = rec.group(1) if rec else None
                item.payment_date = pay.group(1) if pay else None
                item.dividend_per_share = amount
                item.rate = f"{amount:g}" if amount is not None else None
            except Exception as e:
                logger.warning(f"dividend enrich failed {item.edge_no}: {e}")

    await asyncio.gather(*(enrich(i) for i in items[:detail_limit]))
    return items


async def fetch_dividend_history(
    client: httpx.AsyncClient,
    symbols: list[str],
    as_of: datetime | None = None,
    days_back: int = 365,
) -> list[DividendItem]:
    """Supplement PSE disclosures with Yahoo's public per-symbol dividend events."""
    end = as_of or datetime.now()
    start = end - timedelta(days=days_back)
    sem = asyncio.Semaphore(6)
    items: list[DividendItem] = []

    async def fetch_one(symbol: str):
        async with sem:
            try:
                ticker = f"{_normalise_symbol(symbol)}.PS"
                url = (
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                    f"?period1={int(start.timestamp())}&period2={int(end.timestamp())}"
                    "&interval=1d&events=div&includeAdjustedClose=true"
                )
                response = await client.get(url, timeout=20, headers={"User-Agent": UA})
                response.raise_for_status()
                events = (response.json().get("chart", {}).get("result") or [{}])[0].get("events", {}).get("dividends", {})
                for event in events.values():
                    amount = float(event.get("amount") or 0)
                    event_date = datetime.utcfromtimestamp(int(event["date"])).date().isoformat()
                    if amount > 0:
                        items.append(DividendItem(
                            symbol=_normalise_symbol(symbol), company=_normalise_symbol(symbol),
                            title="Yahoo dividend history", disclosure_date=event_date,
                            edge_no=f"yahoo-{_normalise_symbol(symbol)}-{event_date}",
                            ex_date=event_date, rate=f"{amount:g}", dividend_per_share=amount,
                        ))
            except Exception as e:
                logger.warning(f"Yahoo dividend history failed for {symbol}: {e}")

    await asyncio.gather(*(fetch_one(symbol) for symbol in symbols))
    return items
