"""
PSE Daily Market Automation — CORE POC (Phase 1)
Proves in isolation:
  A) Real PSE data fetch: Phisix quotes + Yahoo PSEi/sector indices + PSE Edge dividends
  B) Pydantic validation + deterministic computations (no LLM math)
  C) HTML template -> PNG via Playwright
  D) Manual captions are entered in the dashboard after the data pipeline completes
Run: cd /app && python tests/test_core.py
"""
import asyncio
import os
import re
import sys
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv("/app/backend/.env")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
RESULTS = {}

REIT_TICKERS = {"AREIT", "RCR", "MREIT", "CREIT", "FILRT", "DDMPR", "VREIT", "PREIT"}

SECTOR_TICKERS = {
    "FIN.PS": "Financials", "IND.PS": "Industrial", "HDG.PS": "Holding Firms",
    "PRO.PS": "Property", "SVC.PS": "Services", "M-O.PS": "Mining & Oil",
}


# ---------- Pydantic models (deterministic validation) ----------
class StockQuote(BaseModel):
    symbol: str
    name: str
    price: float = Field(ge=0)
    percent_change: float
    volume: int = Field(ge=0)

    @property
    def value_traded(self) -> float:
        return self.price * self.volume


class IndexQuote(BaseModel):
    symbol: str
    name: str
    value: float
    previous_close: float
    change_points: float
    change_percent: float
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    as_of: datetime


class MarketSummary(BaseModel):
    market_date: date
    psei_value: float
    change_points: float
    change_percent: float
    approx_value_turnover: float
    advancers: int
    decliners: int
    unchanged: int


class DividendItem(BaseModel):
    company: str
    title: str
    disclosure_date: str
    edge_no: str
    ex_date: Optional[str] = None
    record_date: Optional[str] = None
    payment_date: Optional[str] = None
    rate: Optional[str] = None


# ---------- A1: Phisix quotes ----------
async def fetch_phisix(client: httpx.AsyncClient) -> tuple[list[StockQuote], datetime]:
    for url in ["http://phisix-api3.appspot.com/stocks.json", "https://phisix-api4.appspot.com/stocks.json"]:
        try:
            r = await client.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()
            quotes = []
            for s in data["stocks"]:
                quotes.append(StockQuote(
                    symbol=s["symbol"], name=s["name"],
                    price=float(s["price"]["amount"]),
                    percent_change=float(s.get("percentChange") or 0),
                    volume=int(s.get("volume") or 0),
                ))
            as_of = datetime.fromisoformat(data["as_of"])
            return quotes, as_of
        except Exception as e:
            print(f"  phisix source {url} failed: {e}")
    raise RuntimeError("All phisix sources failed")


# ---------- A2: Indices (TradingView primary, Yahoo fallback) ----------
TV_INDEX_TICKERS = {
    "PSE:PSEI": "PSEi", "PSE:ALL": "All Shares", "PSE:FIN": "Financials",
    "PSE:IND": "Industrial", "PSE:HDG": "Holding Firms", "PSE:PRO": "Property",
    "PSE:SVC": "Services", "PSE:M_O": "Mining & Oil",
}


async def fetch_indices_tradingview(client: httpx.AsyncClient) -> dict[str, IndexQuote]:
    payload = {
        "symbols": {"tickers": list(TV_INDEX_TICKERS.keys()), "query": {"types": []}},
        "columns": ["name", "close", "change", "change_abs", "high", "low", "description"],
    }
    r = await client.post("https://scanner.tradingview.com/philippines/scan",
                          json=payload, timeout=25, headers={"User-Agent": UA})
    r.raise_for_status()
    out = {}
    now = datetime.now()
    for row in r.json()["data"]:
        name = TV_INDEX_TICKERS.get(row["s"])
        if not name:
            continue
        _, close, chg_pct, chg_abs, high, low, _desc = row["d"]
        out[name] = IndexQuote(
            symbol=row["s"], name=name, value=round(float(close), 2),
            previous_close=round(float(close) - float(chg_abs), 2),
            change_points=round(float(chg_abs), 2), change_percent=round(float(chg_pct), 2),
            day_high=high, day_low=low, as_of=now,
        )
    return out


async def fetch_yahoo_index(client: httpx.AsyncClient, ticker: str, name: str) -> IndexQuote:
    """Fallback source with retry/backoff (Yahoo rate-limits bursts)."""
    last_err = None
    for attempt, host in enumerate(["query1", "query2"]):
        try:
            url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
            r = await client.get(url, timeout=20, headers={"User-Agent": UA})
            r.raise_for_status()
            meta = r.json()["chart"]["result"][0]["meta"]
            value = float(meta["regularMarketPrice"])
            prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or value)
            return IndexQuote(
                symbol=ticker, name=name, value=value, previous_close=prev,
                change_points=round(value - prev, 2),
                change_percent=round((value - prev) / prev * 100, 2) if prev else 0.0,
                day_high=meta.get("regularMarketDayHigh"), day_low=meta.get("regularMarketDayLow"),
                as_of=datetime.fromtimestamp(meta["regularMarketTime"]),
            )
        except Exception as e:
            last_err = e
            await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Yahoo failed for {ticker}: {last_err}")


# ---------- A3: PSE Edge dividends ----------
async def fetch_dividends(client: httpx.AsyncClient, days_back: int = 21, detail_limit: int = 3) -> list[DividendItem]:
    to_d = datetime.now()
    frm = to_d - timedelta(days=days_back)
    url = ("https://edge.pse.com.ph/companyDisclosures/search.ax?keyword=&tmplNm=Declaration%20of%20Cash%20Dividends"
           f"&fromDate={frm.strftime('%m-%d-%Y')}&toDate={to_d.strftime('%m-%d-%Y')}"
           "&sortType=date&dateSortType=DESC&cmpySortType=ASC&pageNo=1")
    r = await client.get(url, timeout=25, headers={"User-Agent": UA, "Referer": "https://edge.pse.com.ph/announcements/form.do"})
    r.raise_for_status()
    rows = re.findall(r"<tr>(.*?)</tr>", r.text, re.S)
    items = []
    for row in rows[1:]:
        m = re.search(r"openPopup\('([a-f0-9]+)'\).*?>([^<]+)</a>", row, re.S)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if not m or len(cells) < 2:
            continue
        items.append(DividendItem(company="", title=m.group(2).strip(), disclosure_date=cells[1], edge_no=m.group(1)))
    # enrich first N with detail
    for item in items[:detail_limit]:
        try:
            dr = await client.get(f"https://edge.pse.com.ph/openDiscViewer.do?edge_no={item.edge_no}",
                                  timeout=25, headers={"User-Agent": UA})
            fid = re.search(r'downloadHtml\.do\?file_id=(\d+)', dr.text)
            if not fid:
                continue
            fr = await client.get(f"https://edge.pse.com.ph/downloadHtml.do?file_id={fid.group(1)}",
                                  timeout=25, headers={"User-Agent": UA})
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fr.text))
            cn = re.search(r"Exact name of (?:issuer|registrant) as specified in its charter\s+(.{3,80}?)\s+\d{1,2}\.\s", txt)
            item.company = cn.group(1).strip() if cn else "(see disclosure)"
            ex = re.search(r"Ex-?Date\s*:?\s*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})", txt)
            rec = re.search(r"Record Date\s*:?\s*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})", txt)
            pay = re.search(r"Payment Date\s*:?\s*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})", txt)
            rate = re.search(r"(?:Dividend Rate|Rate)\s*:?\s*(?:P(?:hp)?\s*)?([\d,]+\.?\d*)\s*(?:per share|/share)?", txt, re.I)
            item.ex_date = ex.group(1) if ex else None
            item.record_date = rec.group(1) if rec else None
            item.payment_date = pay.group(1) if pay else None
            item.rate = rate.group(1) if rate else None
        except Exception as e:
            print(f"  dividend detail fetch failed for {item.edge_no}: {e}")
    return items


# ---------- B: deterministic computations ----------
def compute(quotes: list[StockQuote], psei: IndexQuote, as_of: datetime):
    common = [q for q in quotes if q.volume > 0]  # traded today
    advancers = sum(1 for q in quotes if q.percent_change > 0)
    decliners = sum(1 for q in quotes if q.percent_change < 0)
    unchanged = sum(1 for q in quotes if q.percent_change == 0)
    turnover = sum(q.value_traded for q in quotes)
    gainers = sorted([q for q in common if q.percent_change > 0], key=lambda q: -q.percent_change)[:5]
    losers = sorted([q for q in common if q.percent_change < 0], key=lambda q: q.percent_change)[:5]
    actives = sorted(common, key=lambda q: -q.value_traded)[:5]
    reits = [q for q in quotes if q.symbol in REIT_TICKERS]
    summary = MarketSummary(
        market_date=as_of.date(), psei_value=psei.value,
        change_points=psei.change_points, change_percent=psei.change_percent,
        approx_value_turnover=round(turnover, 2),
        advancers=advancers, decliners=decliners, unchanged=unchanged,
    )
    return summary, gainers, losers, actives, reits


# ---------- C: Playwright HTML -> PNG ----------
async def render_png(summary: MarketSummary, gainers: list[StockQuote]) -> str:
    from playwright.async_api import async_playwright
    up = summary.change_percent >= 0
    color = "#10b981" if up else "#ef4444"
    arrow = "▲" if up else "▼"
    rows = "".join(
        f'<div class="row"><span class="sym">{q.symbol}</span><span class="price">₱{q.price:,.2f}</span>'
        f'<span class="chg" style="color:#10b981">+{q.percent_change:.2f}%</span></div>'
        for q in gainers
    )
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@400;600;800&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1350px;background:#0a0f1e;color:#f8fafc;font-family:'Inter',sans-serif;padding:72px;display:flex;flex-direction:column}}
.brand{{font-family:'Space Grotesk';font-size:28px;letter-spacing:4px;color:#94a3b8;text-transform:uppercase}}
h1{{font-family:'Space Grotesk';font-size:64px;margin-top:24px;font-weight:700}}
.date{{color:#64748b;font-size:28px;margin-top:8px}}
.hero{{margin-top:64px;background:linear-gradient(135deg,#111a33,#0d1428);border:1px solid #1e293b;border-radius:24px;padding:48px}}
.psei{{font-size:110px;font-weight:800;letter-spacing:-2px}}
.chg{{font-size:44px;font-weight:700;color:{color};margin-top:8px}}
.stats{{display:flex;gap:24px;margin-top:48px}}
.stat{{flex:1;background:#111a33;border:1px solid #1e293b;border-radius:16px;padding:28px}}
.stat .v{{font-size:44px;font-weight:800}}.stat .l{{color:#64748b;font-size:22px;margin-top:6px}}
.movers{{margin-top:48px}}
.movers h2{{font-family:'Space Grotesk';font-size:34px;color:#94a3b8;margin-bottom:20px}}
.row{{display:flex;justify-content:space-between;padding:18px 24px;background:#111a33;border-radius:12px;margin-bottom:10px;font-size:30px}}
.sym{{font-weight:800}}.price{{color:#94a3b8}}
.foot{{margin-top:auto;color:#475569;font-size:22px}}
</style></head><body>
<div class="brand">PSE Daily Pulse</div>
<h1>Market Summary</h1>
<div class="date">{summary.market_date.strftime('%A, %B %d, %Y')}</div>
<div class="hero"><div style="color:#64748b;font-size:30px">PSEi</div>
<div class="psei">{summary.psei_value:,.2f}</div>
<div class="chg">{arrow} {summary.change_points:+,.2f} ({summary.change_percent:+.2f}%)</div></div>
<div class="stats">
<div class="stat"><div class="v" style="color:#10b981">{summary.advancers}</div><div class="l">Advancers</div></div>
<div class="stat"><div class="v" style="color:#ef4444">{summary.decliners}</div><div class="l">Decliners</div></div>
<div class="stat"><div class="v" style="color:#94a3b8">{summary.unchanged}</div><div class="l">Unchanged</div></div>
</div>
<div class="movers"><h2>TOP GAINERS</h2>{rows}</div>
<div class="foot">Approx. value turnover: ₱{summary.approx_value_turnover:,.0f} · Data: PSE via Phisix/Yahoo</div>
</body></html>"""
    out = "/app/tests/poc_market_summary.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=out, full_page=False)
        await browser.close()
    return out


async def main():
    ok = True
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # A1 quotes
        try:
            quotes, as_of = await fetch_phisix(client)
            assert len(quotes) > 200, "too few quotes"
            RESULTS["A1 Phisix quotes"] = f"PASS ({len(quotes)} quotes, as_of={as_of.date()})"
        except Exception as e:
            RESULTS["A1 Phisix quotes"] = f"FAIL: {e}"; ok = False; quotes, as_of = [], datetime.now()

        # A2 indices
        try:
            try:
                indices = await fetch_indices_tradingview(client)
                src = "TradingView"
            except Exception as te:
                print(f"  TradingView failed ({te}); falling back to Yahoo")
                indices = {"PSEi": await fetch_yahoo_index(client, "PSEI.PS", "PSEi")}
                for tk, nm in SECTOR_TICKERS.items():
                    await asyncio.sleep(1.5)
                    indices[nm] = await fetch_yahoo_index(client, tk, nm)
                src = "Yahoo"
            psei = indices["PSEi"]
            sector_count = sum(1 for n in indices if n not in ("PSEi", "All Shares"))
            assert psei.value > 1000 and sector_count >= 6
            RESULTS["A2 Indices (PSEi+sectors)"] = (f"PASS via {src} (PSEi={psei.value:,.2f} {psei.change_percent:+.2f}%, "
                                                    f"{sector_count} sectors e.g. Financials {indices['Financials'].change_percent:+.2f}%)")
        except Exception as e:
            RESULTS["A2 Indices (PSEi+sectors)"] = f"FAIL: {e}"; ok = False; psei = None

        # A3 dividends
        try:
            divs = await fetch_dividends(client)
            assert len(divs) > 0, "no dividend disclosures found"
            d0 = divs[0]
            RESULTS["A3 PSE Edge dividends"] = (f"PASS ({len(divs)} disclosures; first: {d0.company or 'n/a'} "
                                                f"ex={d0.ex_date} rec={d0.record_date} pay={d0.payment_date} rate={d0.rate})")
        except Exception as e:
            RESULTS["A3 PSE Edge dividends"] = f"FAIL: {e}"; ok = False

    # B compute
    try:
        assert quotes and psei
        summary, gainers, losers, actives, reits = compute(quotes, psei, as_of)
        assert summary.advancers + summary.decliners + summary.unchanged == len(quotes)
        assert len(gainers) > 0 and len(reits) >= 5
        RESULTS["B Validation+compute"] = (f"PASS (adv={summary.advancers}/dec={summary.decliners}/unch={summary.unchanged}, "
                                           f"top gainer {gainers[0].symbol} +{gainers[0].percent_change:.2f}%, "
                                           f"top active {actives[0].symbol} ₱{actives[0].value_traded:,.0f}, {len(reits)} REITs)")
    except Exception as e:
        RESULTS["B Validation+compute"] = f"FAIL: {e}"; ok = False; summary, gainers = None, []

    # C render
    try:
        assert summary
        png = await render_png(summary, gainers)
        size = os.path.getsize(png)
        assert size > 30000, f"png too small ({size} bytes)"
        RESULTS["C Playwright PNG render"] = f"PASS ({png}, {size//1024} KB)"
    except Exception as e:
        RESULTS["C Playwright PNG render"] = f"FAIL: {e}"; ok = False

    print("\n" + "=" * 78)
    print("CORE POC RESULTS")
    print("=" * 78)
    for k, v in RESULTS.items():
        print(f"{'✅' if v.startswith('PASS') else '❌'} {k}: {v}")
    print("=" * 78)
    print("OVERALL:", "SUCCESS ✅" if ok else "FAILURE ❌")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
