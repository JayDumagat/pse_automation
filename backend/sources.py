"""Market data sources — resilient fetchers with explicit source fallbacks."""
import asyncio
import json
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
PSE_OFFICIAL_MARKET_URLS = [
    "https://frames.pse.com.ph",
    "https://www.pse.ph/iPse/web/pages/marketInformation.jsp",
    "https://www.pse.com.ph/index-history/",
]
PSE_COMPANY_DIRECTORY_URL = "https://edge.pse.com.ph/companyDirectory/search.ax"
PSE_STOCK_DATA_URL = "https://edge.pse.com.ph/companyPage/stockData.do"
INVESTAGRAM_STOCK_URL = "https://www.investagrams.com/Stock/PSE:{symbol}"
TRADINGVIEW_DIVIDENDS_URL = "https://www.tradingview.com/symbols/PSE-{symbol}/financials-dividends/"
PSE_INDEX_NAMES = {
    "psei": "PSEi",
    "psei total return": "PSEi Total Return",
    "psei total return index": "PSEi Total Return",
    "psei tri": "PSEi Total Return",
    "pseitri": "PSEi Total Return",
    "pse tri": "PSEi Total Return",
    "all shares": "All Shares",
    "financials": "Financials",
    "industrial": "Industrial",
    "holding firms": "Holding Firms",
    "property": "Property",
    "services": "Services",
    "mining and oil": "Mining & Oil",
    "mining & oil": "Mining & Oil",
    "divy": "PSE DivY",
    "pse divy": "PSE DivY",
    "pse divy index": "PSE DivY",
    "dividend yield": "PSE DivY",
    "pse midcap": "PSE MidCap",
    "pse midcap index": "PSE MidCap",
    "midcap": "PSE MidCap",
    "mid cap": "PSE MidCap",
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


def _parse_official_thematic_indices(html: str) -> dict[str, IndexQuote]:
    """Parse thematic/index-history values published by PSE's own pages."""
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, IndexQuote] = {}
    labels = {
        "psei total return": "PSEi Total Return",
        "psei tri": "PSEi Total Return",
        "pse divy": "PSE DivY",
        "pse divy index": "PSE DivY",
        "dividend yield index": "PSE DivY",
        "pse midcap": "PSE MidCap",
        "pse midcap index": "PSE MidCap",
        "midcap index": "PSE MidCap",
    }
    for row in soup.find_all("tr"):
        cells = [re.sub(r"\s+", " ", cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if len(cells) < 2:
            continue
        name = labels.get(cells[0].lower().rstrip(":"))
        value = _first_number(cells[1], signed=False)
        if not name or value is None:
            continue
        change = _first_number(cells[2]) if len(cells) > 2 else None
        percent = _first_number(cells[3]) if len(cells) > 3 else None
        if change is None:
            change = 0.0
        if percent is None:
            previous = value - change
            percent = (change / previous * 100) if previous else 0.0
        out[name] = IndexQuote(
            symbol=name.upper().replace(" ", "_"), name=name,
            value=round(value, 2), previous_close=round(value - change, 2),
            change_points=round(change, 2), change_percent=round(percent, 2),
        )
    return out


def _parse_pse_frames_indices(html: str) -> dict[str, IndexQuote]:
    """Read index quotes from PSE's official embedded market JSON payload."""
    element = BeautifulSoup(html, "html.parser").select_one("#JsonId")
    if not element or not element.get("value"):
        return {}
    try:
        payload = json.loads(element["value"])
    except (TypeError, json.JSONDecodeError):
        return {}

    labels = {
        "psei total return": "PSEi Total Return", "psei tri": "PSEi Total Return",
        "pse divy": "PSE DivY", "pse divy index": "PSE DivY",
        "dividend yield index": "PSE DivY", "pse midcap": "PSE MidCap",
        "pse midcap index": "PSE MidCap", "midcap index": "PSE MidCap",
    }
    result: dict[str, IndexQuote] = {}

    def visit(node):
        if isinstance(node, dict):
            strings = [str(value).strip() for value in node.values() if isinstance(value, str)]
            name = next((labels.get(value.lower().rstrip(":")) for value in strings if value.lower().rstrip(":") in labels), None)
            if name:
                value = next((node[key] for key in ("value", "close", "last", "indexValue", "current", "price") if key in node), None)
                try:
                    value = float(str(value).replace(",", ""))
                except (TypeError, ValueError):
                    value = None
                if value is not None:
                    change = next((node[key] for key in ("change", "change_abs", "changePoints") if key in node), 0)
                    percent = next((node[key] for key in ("percentChange", "changePercent", "percent") if key in node), None)
                    try:
                        change = float(str(change).replace(",", ""))
                    except (TypeError, ValueError):
                        change = 0.0
                    try:
                        percent = float(str(percent).replace(",", "")) if percent is not None else None
                    except (TypeError, ValueError):
                        percent = None
                    previous = value - change
                    result[name] = IndexQuote(
                        symbol=name.upper().replace(" ", "_"), name=name,
                        value=round(value, 2), previous_close=round(previous, 2),
                        change_points=round(change, 2),
                        change_percent=round(percent if percent is not None else ((change / previous * 100) if previous else 0), 2),
                    )
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(payload)
    return result


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
        # PSE Edge's summary page does not include the thematic indices. Read
        # the Exchange's own market/index pages for those values.
        for url in PSE_OFFICIAL_MARKET_URLS:
            try:
                official = await client.get(url, timeout=30, headers={"User-Agent": UA})
                official.raise_for_status()
                parser = _parse_pse_frames_indices if "frames.pse.com.ph" in url else _parse_official_thematic_indices
                for name, value in parser(official.text).items():
                    if name not in indices:
                        indices[name] = value
            except Exception as e:
                logger.warning("Official PSE thematic indices unavailable from %s: %s", url, e)
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


async def fetch_tradingview_stock_metrics(
    client: httpx.AsyncClient,
    symbols: list[str],
) -> dict[str, dict]:
    """Fetch trailing dividend metrics for selected PSE stocks from TradingView."""
    targets = [_normalise_symbol(symbol) for symbol in symbols if _normalise_symbol(symbol)]
    if not targets:
        return {}
    columns = [
        "name", "close", "dividends_yield", "dividends_yield_current",
        "dividend_yield_recent", "dps_common_stock_prim_issue_ttm",
    ]
    payload = {
        "symbols": {
            "tickers": [f"PSE:{symbol}" for symbol in targets],
            "query": {"types": []},
        },
        "columns": columns,
    }
    response = await client.post(
        "https://scanner.tradingview.com/philippines/scan",
        json=payload,
        timeout=25,
        headers={"User-Agent": UA},
    )
    response.raise_for_status()
    metrics: dict[str, dict] = {}
    for row in response.json().get("data", []):
        symbol = _normalise_symbol(str(row.get("s", "")).split(":")[-1])
        if symbol not in targets:
            continue
        values = dict(zip(columns, row.get("d", [])))
        yield_value = next(
            (values.get(field) for field in (
                "dividends_yield", "dividends_yield_current", "dividend_yield_recent",
            ) if values.get(field) is not None),
            None,
        )
        dps = values.get("dps_common_stock_prim_issue_ttm")
        metrics[symbol] = {
            "yield_ttm": round(float(yield_value), 4) if yield_value is not None else None,
            "dividend_per_share_ttm": round(float(dps), 8) if dps is not None else None,
            "yield_source": "tradingview" if yield_value is not None else None,
        }

    # The public dividends page is the canonical presentation of the TTM
    # figure.  Read it for every target so a generic scanner yield cannot
    # silently replace the value shown on the linked source page.  Scanner
    # values remain a fallback when a symbol page is unavailable.
    async def fetch_page(symbol: str):
        try:
            page = await client.get(
                TRADINGVIEW_DIVIDENDS_URL.format(symbol=symbol),
                timeout=25,
                headers={"User-Agent": UA},
            )
            page.raise_for_status()
            text = BeautifulSoup(page.text, "html.parser").get_text(" ", strip=True)
            match = re.search(r"dividend\s+yield\s*\(TTM\)%\s+is\s+([\d,.]+)%", text, re.I)
            if not match:
                return
            current = metrics.setdefault(symbol, {})
            current["yield_ttm"] = round(float(match.group(1).replace(",", "")), 4)
            current["yield_source"] = "tradingview"
        except Exception as e:
            logger.warning("TradingView dividend page failed for %s: %s", symbol, e)

    await asyncio.gather(*(fetch_page(symbol) for symbol in targets))
    return metrics


def _parse_pse_company_ids(html: str, target_symbols: set[str]) -> dict[str, tuple[str, str]]:
    """Map PSE symbols to company/security IDs from the public directory."""
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, tuple[str, str]] = {}
    # In the current directory markup the company name and ticker are sibling
    # cells, while the cmDetail(...) handler is attached to the company-name
    # link.  Parse the whole row so the two pieces are associated correctly.
    for row in soup.find_all("tr"):
        cells = [re.sub(r"\s+", " ", cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        symbol = next((_normalise_symbol(cell) for cell in cells if _normalise_symbol(cell) in target_symbols), "")
        if not symbol or symbol in found:
            continue
        link_data = " ".join(
            " ".join((anchor.get("onclick", ""), anchor.get("href", "")))
            for anchor in row.select("a[onclick], a[href]")
        )
        match = re.search(r"cmDetail\(\s*['\"]?(\d+)['\"]?\s*(?:,\s*['\"]?(\d+)['\"]?)?\s*\)", link_data, re.I)
        if not match:
            cmpy = re.search(r"(?:cmpy_id|company_id)[=/'\"]+\s*(\d+)", link_data, re.I)
            match = re.match(r"(\d+)$", cmpy.group(1)) if cmpy else None
        if match:
            found[symbol] = (match.group(1), match.group(2) if match.lastindex and match.lastindex >= 2 and match.group(2) else "")

    # Keep support for older responses where the ticker itself was the link.
    for anchor in soup.select("a[onclick], a[href]"):
        symbol = _normalise_symbol(anchor.get_text(" ", strip=True))
        if symbol not in target_symbols or symbol in found:
            continue
        link_data = " ".join((anchor.get("onclick", ""), anchor.get("href", "")))
        # PSE has used both cmDetail(cmpy_id, security_id) and direct links
        # with only cmpy_id over time.  The stock-data page accepts the latter.
        match = re.search(r"cmDetail\(\s*['\"]?(\d+)['\"]?\s*(?:,\s*['\"]?(\d+)['\"]?)?\s*\)", link_data, re.I)
        if not match:
            cmpy = re.search(r"(?:cmpy_id|company_id)[=/'\"]+\s*(\d+)", link_data, re.I)
            match = re.match(r"(\d+)$", cmpy.group(1)) if cmpy else None
        if match:
            found[symbol] = (match.group(1), match.group(2) if match.lastindex and match.lastindex >= 2 and match.group(2) else "")
    return found


async def fetch_board_lots(client: httpx.AsyncClient, symbols: list[str]) -> dict[str, int]:
    """Fetch exact per-security Board Lot values from PSE Edge stock pages."""
    targets = {_normalise_symbol(symbol) for symbol in symbols if _normalise_symbol(symbol)}
    if not targets:
        return {}
    # search.ax is paginated (the form.do shell contains no company rows).
    pages = await asyncio.gather(*(
        client.get(PSE_COMPANY_DIRECTORY_URL, params={"pageNo": page}, timeout=30, headers={"User-Agent": UA})
        for page in range(1, 7)
    ))
    for page in pages:
        page.raise_for_status()
    company_ids: dict[str, tuple[str, str]] = {}
    for page in pages:
        company_ids.update(_parse_pse_company_ids(page.text, targets - set(company_ids)))
    if not company_ids:
        raise ValueError("PSE Edge company directory did not contain the requested tickers")

    sem = asyncio.Semaphore(6)
    lots: dict[str, int] = {}

    async def fetch_one(symbol: str, ids: tuple[str, str]):
        async with sem:
            try:
                response = await client.get(
                    PSE_STOCK_DATA_URL,
                    params={"cmpy_id": ids[0], **({"security_id": ids[1]} if ids[1] else {})},
                    timeout=25,
                    headers={"User-Agent": UA, "Referer": PSE_COMPANY_DIRECTORY_URL},
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                for row in soup.find_all("tr"):
                    cells = row.find_all(["th", "td"])
                    if len(cells) < 2:
                        continue
                    label = re.sub(r"\s+", " ", cells[0].get_text(" ", strip=True)).strip().lower().rstrip(":")
                    if label not in {"board lot", "board lot (shares)"}:
                        continue
                    match = re.search(r"\d[\d,]*", cells[1].get_text(" ", strip=True))
                    if match:
                        lots[symbol] = int(match.group(0).replace(",", ""))
                    return
                logger.warning("PSE Edge Board Lot field missing for %s", symbol)
            except Exception as e:
                logger.warning("PSE Edge Board Lot fetch failed for %s: %s", symbol, e)

    await asyncio.gather(*(fetch_one(symbol, ids) for symbol, ids in company_ids.items()))
    return lots


def _parse_human_count(value: str) -> int | None:
    """Parse Investagrams values such as 5.51K or 1.2M into an integer."""
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*([KMB])?", value or "", re.I)
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(
        (match.group(2) or "").upper(), 1,
    )
    return int(round(number * multiplier))


async def fetch_investagram_trade_counts(symbols: list[str]) -> dict[str, int]:
    """Scrape latest Trades values from each Investagrams Historical Data tab."""
    targets = [_normalise_symbol(symbol) for symbol in symbols if _normalise_symbol(symbol)]
    if not targets:
        return {}
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        logger.warning("Investagrams trade scraper unavailable: %s", e)
        return {}

    counts: dict[str, int] = {}
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(user_agent=UA)
            page = await context.new_page()
            for symbol in targets:
                try:
                    await page.goto(
                        INVESTAGRAM_STOCK_URL.format(symbol=symbol),
                        wait_until="domcontentloaded",
                        timeout=35_000,
                    )
                    await page.get_by_text("Historical Data", exact=True).click(timeout=15_000)
                    rows = page.locator("#stockHistoricalData table tbody tr")
                    await rows.first.wait_for(state="attached", timeout=20_000)
                    for index in range(min(await rows.count(), 10)):
                        cells = await rows.nth(index).locator("td").all_text_contents()
                        if len(cells) < 11:
                            continue
                        trades = _parse_human_count(cells[-1])
                        if trades is not None:
                            counts[symbol] = trades
                            break
                except Exception as e:
                    logger.warning("Investagrams trade count fetch failed for %s: %s", symbol, e)
                await page.wait_for_timeout(250)
            await browser.close()
    except Exception as e:
        logger.warning("Investagrams trade scraper failed: %s", e)
    return counts


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
