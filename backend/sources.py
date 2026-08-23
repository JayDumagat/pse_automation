"""Market data sources — resilient fetchers with fallbacks.
Primary quotes: Phisix (community JSON mirror of PSE quotes)
Primary indices: TradingView scanner (single POST, PSEi + sectors)
Fallback indices: Yahoo Finance chart API (per-ticker, retry/backoff)
Dividends: PSE Edge disclosure search + detail parsing
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta

import httpx

from models import DividendItem, IndexQuote, StockQuote

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
                    quotes.append(StockQuote(
                        symbol=s["symbol"], name=s["name"], price=price,
                        percent_change=float(s.get("percentChange") or 0),
                        volume=volume, value_traded=round(price * volume, 2),
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


async def fetch_dividends(client: httpx.AsyncClient, days_back: int = 21, detail_limit: int = 8) -> list[DividendItem]:
    """Cash dividend declarations from PSE Edge, enriched with ex/record/payment dates."""
    to_d = datetime.now()
    frm = to_d - timedelta(days=days_back)
    url = ("https://edge.pse.com.ph/companyDisclosures/search.ax?keyword=&tmplNm=Declaration%20of%20Cash%20Dividends"
           f"&fromDate={frm.strftime('%m-%d-%Y')}&toDate={to_d.strftime('%m-%d-%Y')}"
           "&sortType=date&dateSortType=DESC&cmpySortType=ASC&pageNo=1")
    r = await client.get(url, timeout=30, headers={"User-Agent": UA, "Referer": "https://edge.pse.com.ph/announcements/form.do"})
    r.raise_for_status()
    rows = re.findall(r"<tr>(.*?)</tr>", r.text, re.S)
    items: list[DividendItem] = []
    for row in rows[1:]:
        m = re.search(r"openPopup\('([a-f0-9]+)'\).*?>([^<]+)</a>", row, re.S)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if not m or len(cells) < 2:
            continue
        items.append(DividendItem(title=m.group(2).strip(), disclosure_date=cells[1], edge_no=m.group(1)))
    sem = asyncio.Semaphore(3)

    async def enrich(item: DividendItem):
        async with sem:
            try:
                dr = await client.get(f"https://edge.pse.com.ph/openDiscViewer.do?edge_no={item.edge_no}",
                                      timeout=25, headers={"User-Agent": UA})
                fid = re.search(r"downloadHtml\.do\?file_id=(\d+)", dr.text)
                if not fid:
                    return
                fr = await client.get(f"https://edge.pse.com.ph/downloadHtml.do?file_id={fid.group(1)}",
                                      timeout=25, headers={"User-Agent": UA})
                txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fr.text))
                cn = re.search(r"Exact name of (?:issuer|registrant) as specified in its charter\s+(.{3,80}?)\s+\d{1,2}\.\s", txt)
                item.company = cn.group(1).strip() if cn else ""
                ex = re.search(r"Ex-?Date\s*:?\s*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})", txt)
                rec = re.search(r"Record Date\s*:?\s*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})", txt)
                pay = re.search(r"Payment Date\s*:?\s*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})", txt)
                rate = re.search(r"Dividend Rate\s*:?\s*(?:P(?:hp)?\.?\s*)?([\d,]+\.?\d*)", txt, re.I)
                item.ex_date = ex.group(1) if ex else None
                item.record_date = rec.group(1) if rec else None
                item.payment_date = pay.group(1) if pay else None
                item.rate = rate.group(1) if rate else None
            except Exception as e:
                logger.warning(f"dividend enrich failed {item.edge_no}: {e}")

    await asyncio.gather(*(enrich(i) for i in items[:detail_limit]))
    return items
