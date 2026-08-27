"""Three-slide cinematic PSE Market Wrap templates."""
import base64
from datetime import datetime
from html import escape
from pathlib import Path

GAIN = "#55e6b1"
LOSS = "#ff6b72"

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}html,body{width:1080px;height:1350px;overflow:hidden}
body{background:#090b10;color:#f5f0e8;font-family:Manrope,Arial,sans-serif;position:relative}
.wrap{height:100%;padding:62px 68px 58px;position:relative;display:flex;flex-direction:column;overflow:hidden}
.kicker{font:500 18px/1 DM Mono,monospace;letter-spacing:3px;text-transform:uppercase;color:#b4b7bd;position:relative;z-index:4}
.date{font:400 17px/1 DM Mono,monospace;color:#8b8f98;margin-top:12px;position:relative;z-index:4}
.headline{font-size:68px;line-height:.98;letter-spacing:-3px;font-weight:800;max-width:880px;position:relative;z-index:4}
.subhead{font-size:22px;line-height:1.35;color:#c8c7c2;max-width:730px;position:relative;z-index:4}
.mono{font-family:'DM Mono',monospace}.rule{height:1px;background:rgba(245,240,232,.25);position:relative;z-index:4}
.hero{position:absolute;inset:0;overflow:hidden;background:#0a0d13}.hero:after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(5,7,10,.06),rgba(5,7,10,.12) 34%,#090b10 86%)}
.grid{position:absolute;inset:-20%;background:linear-gradient(115deg,transparent 48%,rgba(85,230,177,.13) 48.2%,transparent 48.6%),linear-gradient(25deg,transparent 65%,rgba(245,240,232,.09) 65.2%,transparent 65.5%);transform:perspective(500px) rotateX(52deg) rotateZ(-12deg);opacity:.55}
.orb{position:absolute;border-radius:50%;filter:blur(2px);mix-blend-mode:screen}.coin{position:absolute;border:2px solid rgba(245,240,232,.35);border-radius:50%;display:flex;align-items:center;justify-content:center;color:rgba(245,240,232,.35);font:500 96px DM Mono,monospace;transform:rotate(-18deg);box-shadow:0 0 80px rgba(85,230,177,.12),inset 0 0 50px rgba(245,240,232,.08)}
.stat{position:relative;z-index:4}.value{font-size:116px;line-height:.9;letter-spacing:-6px;font-weight:800}.change{font-size:38px;font-weight:700;margin-top:16px}.label{font:500 16px DM Mono,monospace;letter-spacing:2px;text-transform:uppercase;color:#a5a8af}
.bottom{margin-top:auto;position:relative;z-index:4}.footer{display:flex;justify-content:space-between;align-items:end;font:400 14px DM Mono,monospace;color:#7e828a;margin-top:28px}
.driver{display:grid;grid-template-columns:1fr auto;gap:12px 26px;position:relative;z-index:4;font-size:25px}.driver span:nth-child(2n){font-family:DM Mono,monospace;text-align:right}.positive{color:#55e6b1}.negative{color:#ff6b72}
.watch-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;position:relative;z-index:4}.watch{border-top:1px solid rgba(245,240,232,.35);padding-top:16px}.watch-title{font-size:22px;font-weight:700}.watch-copy{font-size:17px;color:#aeb0b5;line-height:1.4;margin-top:7px}
"""


def _date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y").upper()
    except Exception:
        return str(value).upper()


def _short_money(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1e9:
        return f"₱{value / 1e9:.2f}B"
    if value >= 1e6:
        return f"₱{value / 1e6:.1f}M"
    return f"₱{value:,.0f}"


def _asset_uri(path: str | Path | None) -> str | None:
    if not path or not Path(path).is_file():
        return None
    file_path = Path(path)
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(file_path.suffix.lower())
    if not mime:
        return None
    return f"data:{mime};base64,{base64.b64encode(file_path.read_bytes()).decode('ascii')}"


def _shell(content: str, theme: str, background: str | Path | None = None) -> str:
    uri = _asset_uri(background)
    photo = f"background-image:url('{uri}');background-size:cover;background-position:center" if uri else ""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{BASE_CSS}</style></head><body><div class='hero {theme}' style=\"{photo}\"></div>{content}</body></html>"


def _header(snapshot: dict, brand: str) -> str:
    return (f"<div class='wrap'><div class='kicker'>{escape(brand)} · PSE MARKET WRAP</div>"
            f"<div class='date'>{_date(snapshot['summary']['market_date'])}</div>"
            f"<div class='rule' style='margin-top:24px'></div>")


def _footer() -> str:
    return "<div class='footer'><span>PSE DATA · DAILY CLOSE</span><span>NOT FINANCIAL ADVICE</span></div></div>"


def _story_headline(snapshot: dict) -> str:
    s = snapshot["summary"]
    sectors = [x for x in snapshot.get("sectors", []) if x.get("change_percent") is not None]
    strongest = max(sectors, key=lambda x: x["change_percent"], default=None)
    weakest = min(sectors, key=lambda x: x["change_percent"], default=None)
    if s["change_percent"] > 0 and s["advancers"] >= s["decliners"]:
        return "PHILIPPINE STOCKS EXTEND THE RALLY"
    if s["change_percent"] < 0 and s["decliners"] > s["advancers"]:
        return f"{weakest['name'].upper()} LEADS THE RETREAT" if weakest and weakest["change_percent"] < 0 else "PSEI SLIPS AS SELLING BROADENS"
    if strongest and weakest and strongest["change_percent"] > 0:
        return f"{strongest['name'].upper()} CUSHIONS A MIXED SESSION"
    return "PSEI HOLDS THE MARKET'S ATTENTION"


def _backgrounds() -> dict[str, Path | None]:
    root = Path(__file__).resolve().parent / "storage" / "assets"
    return {
        key: next((root / f"background-{number}.{ext}" for ext in ("jpg", "jpeg", "png", "webp") if (root / f"background-{number}.{ext}").is_file()), None)
        for key, number in (("big-move", 1), ("market-drivers", 2), ("whats-next", 3))
    }


def _supporting_stats(snapshot: dict) -> str:
    s = snapshot["summary"]
    values = []
    all_shares = snapshot.get("indices", {}).get("All Shares", {})
    if all_shares.get("change_percent") is not None:
        values.append(("ALL SHARES", f"{all_shares['change_percent']:+.2f}%"))
    values.extend([
        ("BREADTH", f"{s['advancers']} / {s['decliners']} / {s['unchanged']}"),
        ("VALUE TURNOVER", _short_money(s.get("value_turnover", s.get("approx_value_turnover")))),
    ])
    if s.get("total_volume"):
        values.append(("TOTAL VOLUME", f"{s['total_volume']:,}"))
    if s.get("total_trades") is not None:
        values.append(("TRADES", f"{s['total_trades']:,}"))
    return "<div style='display:flex;flex-wrap:wrap;gap:26px 45px;margin-top:30px'>" + "".join(
        f"<div><div class='label'>{label}</div><div class='mono' style='font-size:30px;margin-top:8px'>{value}</div></div>"
        for label, value in values[:5]
    ) + "</div>"


def big_move_html(snapshot: dict, brand: str, background: str | Path | None = None) -> str:
    s = snapshot["summary"]
    up = s["change_percent"] >= 0
    color = GAIN if up else LOSS
    verb = "rose" if up else "fell"
    takeaway = f"The benchmark {verb} as {s['advancers']} names advanced against {s['decliners']} decliners."
    content = _header(snapshot, brand) + f"""
<div class='grid'></div><div class='orb' style='width:620px;height:620px;right:-170px;top:170px;background:radial-gradient(circle at 35% 35%,rgba(85,230,177,.42),rgba(23,90,87,.12) 35%,transparent 70%)'></div><div class='coin' style='width:520px;height:520px;right:-72px;top:202px'>₱</div>
<div style='margin-top:105px;position:relative;z-index:4'><div class='label'>THE BIG MOVE</div><div class='headline' style='margin-top:16px'>{escape(_story_headline(snapshot))}</div><div class='subhead' style='margin-top:24px'>{escape(takeaway)}</div></div>
<div class='bottom'><div class='stat'><div class='label'>PSEI CLOSE</div><div class='value'>{s['psei_value']:,.2f}</div><div class='change' style='color:{color}'>{s['change_percent']:+.2f}% <span class='mono' style='font-size:22px;color:#b4b7bd'>/ {s['change_points']:+,.2f} pts</span></div></div><div class='subhead' style='margin-top:30px;max-width:610px'>{escape(s.get('explanation',''))}</div>{_footer()}"""
    return _shell(content.replace("</div><div class='subhead' style='margin-top:30px", _supporting_stats(snapshot) + "<div class='subhead' style='margin-top:30px"), "hero-move", background)


def market_drivers_html(snapshot: dict, brand: str, background: str | Path | None = None) -> str:
    s = snapshot["summary"]
    sectors = [x for x in snapshot.get("sectors", []) if x.get("change_percent") is not None]
    strongest = max(sectors, key=lambda x: x["change_percent"], default=None)
    weakest = min(sectors, key=lambda x: x["change_percent"], default=None)
    gain = (snapshot.get("gainers") or [{}])[0]
    loss = (snapshot.get("losers") or [{}])[0]
    pairs = [("LEADING SECTOR", f"{strongest['name']}  {strongest['change_percent']:+.2f}%" if strongest else "Unavailable", "positive" if strongest and strongest["change_percent"] >= 0 else "negative"), ("WEAKEST SECTOR", f"{weakest['name']}  {weakest['change_percent']:+.2f}%" if weakest else "Unavailable", "negative" if weakest and weakest["change_percent"] < 0 else "positive"), ("TOP GAINER", f"{gain.get('symbol','—')}  {gain.get('percent_change',0):+.2f}%", "positive"), ("TOP LOSER", f"{loss.get('symbol','—')}  {loss.get('percent_change',0):+.2f}%", "negative")]
    pairs = []
    for label, movers, css in (("MARKET LEADERS", snapshot.get("gainers", [])[:3], "positive"), ("UNDER PRESSURE", snapshot.get("losers", [])[:3], "negative")):
        for mover in movers:
            if mover.get("percent_change") is not None:
                pairs.append((label, f"{mover.get('symbol', '')}  {mover['percent_change']:+.2f}%", css))
                label = ""
    for sector in sectors[:6]:
        pairs.append((sector.get("name", "SECTOR"), f"{sector['change_percent']:+.2f}%", "positive" if sector["change_percent"] >= 0 else "negative"))
    for active_row in (snapshot.get("actives") or [])[:3]:
        if active_row.get("value_traded") is not None:
            pairs.append((f"ACTIVE {active_row.get('symbol', '')}", f"{_short_money(active_row['value_traded'])}  {active_row.get('percent_change', 0):+.2f}%", "positive" if active_row.get("percent_change", 0) >= 0 else "negative"))
    rows = "".join(f"<span class='label'>{a}</span><span class='{c}'>{escape(b)}</span>" for a,b,c in pairs)
    content = _header(snapshot, brand) + f"""
<div class='orb' style='width:780px;height:780px;left:-300px;top:210px;background:radial-gradient(circle,rgba(255,107,114,.34),rgba(93,37,50,.1) 43%,transparent 70%)'></div><div class='grid' style='opacity:.3'></div>
<div style='margin-top:82px;position:relative;z-index:4'><div class='headline'>WHAT MOVED<br>THE MARKET</div><div class='subhead' style='margin-top:22px'>A session shaped by breadth, sector rotation and the names that pulled attention.</div></div>
<div class='bottom'><div class='driver'>{rows}</div><div class='rule' style='margin-top:34px'></div><div style='display:flex;gap:55px;margin-top:24px;position:relative;z-index:4'><div><div class='label'>BREADTH</div><div class='mono' style='font-size:30px;margin-top:8px'>{s['advancers']} ↑  /  {s['decliners']} ↓</div></div><div><div class='label'>VALUE TURNOVER</div><div class='mono' style='font-size:30px;margin-top:8px'>{_short_money(s.get('value_turnover', s.get('approx_value_turnover')))}</div></div></div>{_footer()}"""
    return _shell(content, "hero-drivers", background)


def next_html(snapshot: dict, brand: str, background: str | Path | None = None) -> str:
    sectors = sorted((x for x in snapshot.get("sectors", []) if x.get("change_percent") is not None), key=lambda x: abs(x["change_percent"]), reverse=True)
    sector_name = sectors[0]["name"] if sectors else "sector rotation"
    active = (snapshot.get("actives") or [{}])[0]
    content = _header(snapshot, brand) + f"""
<div class='grid' style='opacity:.28'></div><div class='orb' style='width:900px;height:900px;right:-380px;top:110px;background:radial-gradient(circle,rgba(119,149,255,.28),rgba(32,43,104,.1) 42%,transparent 70%)'></div>
<div style='margin-top:115px;position:relative;z-index:4'><div class='headline'>WHAT'S<br>NEXT</div><div class='subhead' style='margin-top:24px'>Keep the lens on the next catalyst, not just the last close.</div></div>
<div class='bottom'><div class='watch-grid'><div class='watch'><div class='watch-title'>PSEi follow-through</div><div class='watch-copy'>Watch whether today's move extends into the next session.</div></div><div class='watch'><div class='watch-title'>{escape(sector_name)}</div><div class='watch-copy'>The day's largest sector move remains a key read on rotation.</div></div><div class='watch'><div class='watch-title'>{escape(active.get('symbol','Market activity'))}</div><div class='watch-copy'>Most active by value in the latest PSE close.</div></div><div class='watch'><div class='watch-title'>Global pulse</div><div class='watch-copy'>Track FX, oil and overnight risk appetite before the open.</div></div></div><div class='stat' style='margin-top:44px'><div class='label'>NEXT SESSION MARKER</div><div style='font-size:42px;font-weight:700;margin-top:9px'>PSE OPEN · WATCH THE TAPE</div></div>{_footer()}"""
    return _shell(content, "hero-next", background)


def build_all(snapshot: dict, dividends: list[dict], brand: str) -> dict[str, str]:
    backgrounds = _backgrounds()
    return {
        "big-move": big_move_html(snapshot, brand, backgrounds["big-move"]),
        "market-drivers": market_drivers_html(snapshot, brand, backgrounds["market-drivers"]),
        "whats-next": next_html(snapshot, brand, backgrounds["whats-next"]),
    }
