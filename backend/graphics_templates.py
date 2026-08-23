"""Version-controlled HTML/CSS templates for the 5 social graphics (1080x1350).
Validated JSON in -> HTML out -> Playwright screenshot -> PNG.
"""
from datetime import date, datetime

GAIN = "#2EE59D"
LOSS = "#FF5C6C"
MUTED = "#8b9bbd"
FAINT = "#5b6a8a"

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:#0a0f1e;color:#f8fafc;font-family:'Inter',sans-serif;padding:64px;display:flex;flex-direction:column;position:relative;overflow:hidden}
body::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 900px 500px at 85% -10%, rgba(46,110,229,0.14), transparent),radial-gradient(ellipse 700px 400px at -10% 110%, rgba(46,229,157,0.06), transparent);pointer-events:none}
.brand{font-family:'Space Grotesk';font-size:26px;letter-spacing:5px;color:#8b9bbd;text-transform:uppercase;font-weight:500}
h1{font-family:'Space Grotesk';font-size:58px;margin-top:18px;font-weight:700;letter-spacing:-1px}
.date{color:#5b6a8a;font-size:26px;margin-top:8px;font-weight:500}
.card{background:linear-gradient(135deg,#111a33,#0d1428);border:1px solid #1e2a47;border-radius:22px}
.foot{margin-top:auto;color:#44536f;font-size:20px;display:flex;justify-content:space-between;align-items:center;padding-top:24px}
.pill{background:#111a33;border:1px solid #1e2a47;border-radius:999px;padding:8px 20px;font-size:20px;color:#8b9bbd}
"""


def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%A, %B %d, %Y")
    except Exception:
        return iso


def _peso_short(v: float) -> str:
    if v >= 1e9:
        return f"\u20b1{v/1e9:.2f}B"
    if v >= 1e6:
        return f"\u20b1{v/1e6:.1f}M"
    return f"\u20b1{v:,.0f}"


def _shell(title: str, subtitle: str, body: str, brand: str = "PSE Daily Pulse", footer_note: str = "Data: PSE via Phisix \u00b7 TradingView \u00b7 PSE Edge") -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_CSS}</style></head><body>
<div class="brand">{brand}</div>
<h1>{title}</h1>
<div class="date">{subtitle}</div>
{body}
<div class="foot"><span>{footer_note}</span><span>Not financial advice</span></div>
</body></html>"""


def market_summary_html(snapshot: dict, brand: str) -> str:
    s = snapshot["summary"]
    up = s["change_percent"] >= 0
    color = GAIN if up else LOSS
    arrow = "\u25b2" if up else "\u25bc"
    gainers = snapshot["gainers"][:3]
    losers = snapshot["losers"][:3]

    def mini_rows(rows, positive):
        out = ""
        for q in rows:
            c = GAIN if positive else LOSS
            sign = "+" if positive else ""
            out += (f'<div style="display:flex;justify-content:space-between;padding:14px 20px;background:#0d1630;'
                    f'border-radius:12px;margin-bottom:8px;font-size:26px;border:1px solid #16203c">'
                    f'<span style="font-weight:800">{q["symbol"]}</span>'
                    f'<span style="color:{c};font-weight:700">{sign}{q["percent_change"]:.2f}%</span></div>')
        return out or '<div style="color:#5b6a8a;font-size:24px;padding:14px 20px">None today</div>'

    body = f"""
<div class="card" style="margin-top:44px;padding:42px 48px">
  <div style="color:#5b6a8a;font-size:28px;font-weight:600;letter-spacing:2px">PSEi CLOSE</div>
  <div style="font-size:104px;font-weight:800;letter-spacing:-3px;font-family:'Space Grotesk'">{s['psei_value']:,.2f}</div>
  <div style="font-size:42px;font-weight:700;color:{color};margin-top:4px">{arrow} {s['change_points']:+,.2f} ({s['change_percent']:+.2f}%)</div>
</div>
<div style="display:flex;gap:20px;margin-top:24px">
  <div class="card" style="flex:1;padding:24px 28px"><div style="font-size:42px;font-weight:800;color:{GAIN}">{s['advancers']}</div><div style="color:#8b9bbd;font-size:22px;margin-top:4px">Advancers</div></div>
  <div class="card" style="flex:1;padding:24px 28px"><div style="font-size:42px;font-weight:800;color:{LOSS}">{s['decliners']}</div><div style="color:#8b9bbd;font-size:22px;margin-top:4px">Decliners</div></div>
  <div class="card" style="flex:1;padding:24px 28px"><div style="font-size:42px;font-weight:800;color:#8b9bbd">{s['unchanged']}</div><div style="color:#8b9bbd;font-size:22px;margin-top:4px">Unchanged</div></div>
  <div class="card" style="flex:1.4;padding:24px 28px"><div style="font-size:42px;font-weight:800">{_peso_short(s['approx_value_turnover'])}</div><div style="color:#8b9bbd;font-size:22px;margin-top:4px">Approx. turnover</div></div>
</div>
<div style="display:flex;gap:24px;margin-top:32px">
  <div style="flex:1"><div style="font-family:'Space Grotesk';font-size:26px;color:{GAIN};letter-spacing:2px;margin-bottom:14px">TOP GAINERS</div>{mini_rows(gainers, True)}</div>
  <div style="flex:1"><div style="font-family:'Space Grotesk';font-size:26px;color:{LOSS};letter-spacing:2px;margin-bottom:14px">TOP LOSERS</div>{mini_rows(losers, False)}</div>
</div>"""
    return _shell("Market Summary", _fmt_date(s["market_date"]), body, brand)


def movers_html(snapshot: dict, brand: str) -> str:
    s = snapshot["summary"]

    def block(title, rows, mode):
        out = f'<div style="font-family:\'Space Grotesk\';font-size:26px;letter-spacing:2px;margin:26px 0 12px;color:#8b9bbd">{title}</div>'
        for i, q in enumerate(rows[:5]):
            if mode == "active":
                right = f'<span style="font-weight:700;color:#c7d3ec">{_peso_short(q["value_traded"])}</span>'
            else:
                c = GAIN if q["percent_change"] >= 0 else LOSS
                right = f'<span style="font-weight:800;color:{c}">{q["percent_change"]:+.2f}%</span>'
            out += (f'<div style="display:flex;align-items:center;gap:18px;padding:13px 22px;background:#0d1630;'
                    f'border:1px solid #16203c;border-radius:12px;margin-bottom:7px;font-size:27px">'
                    f'<span style="color:#44536f;font-weight:700;width:34px">{i+1}</span>'
                    f'<span style="font-weight:800;flex:1">{q["symbol"]}</span>'
                    f'<span style="color:#8b9bbd">\u20b1{q["price"]:,.2f}</span>{right}</div>')
        return out

    body = ('<div style="margin-top:8px">'
            + block("TOP GAINERS", snapshot["gainers"], "gain")
            + block("TOP LOSERS", snapshot["losers"], "loss")
            + block("MOST ACTIVE BY VALUE", snapshot["actives"], "active")
            + "</div>")
    return _shell("Top Movers", _fmt_date(s["market_date"]), body, brand)


def sectors_html(snapshot: dict, brand: str) -> str:
    s = snapshot["summary"]
    sectors = snapshot["sectors"]
    max_abs = max((abs(x["change_percent"]) for x in sectors), default=1) or 1
    rows = ""
    for sec in sectors:
        up = sec["change_percent"] >= 0
        c = GAIN if up else LOSS
        w = max(6, int(abs(sec["change_percent"]) / max_abs * 100))
        rows += f"""
<div class="card" style="padding:26px 32px;margin-bottom:16px">
  <div style="display:flex;justify-content:space-between;align-items:baseline">
    <span style="font-size:32px;font-weight:700">{sec['name']}</span>
    <span style="font-size:32px;font-weight:800;color:{c}">{sec['change_percent']:+.2f}%</span>
  </div>
  <div style="display:flex;justify-content:space-between;color:#5b6a8a;font-size:23px;margin-top:6px">
    <span>{sec['value']:,.2f}</span><span>{sec['change_points']:+,.2f} pts</span>
  </div>
  <div style="height:10px;background:#0d1630;border-radius:6px;margin-top:14px;overflow:hidden">
    <div style="height:100%;width:{w}%;background:{c};border-radius:6px"></div>
  </div>
</div>"""
    psei = snapshot["indices"]["PSEi"]
    up = psei["change_percent"] >= 0
    body = f"""
<div style="margin-top:30px;display:flex;gap:16px;margin-bottom:26px">
  <span class="pill">PSEi {psei['value']:,.2f} <b style="color:{GAIN if up else LOSS}">{psei['change_percent']:+.2f}%</b></span>
  <span class="pill">Breadth {s['advancers']}\u25b2 / {s['decliners']}\u25bc</span>
</div>
{rows}"""
    return _shell("Sector Performance", _fmt_date(s["market_date"]), body, brand)


def reits_html(snapshot: dict, brand: str) -> str:
    s = snapshot["summary"]
    rows = ""
    for q in snapshot["reits"][:8]:
        up = q["percent_change"] >= 0
        c = GAIN if up else (LOSS if q["percent_change"] < 0 else MUTED)
        rows += (f'<div style="display:flex;align-items:center;padding:22px 30px;background:#0d1630;border:1px solid #16203c;'
                 f'border-radius:14px;margin-bottom:12px;font-size:30px">'
                 f'<span style="font-weight:800;width:200px">{q["symbol"]}</span>'
                 f'<span style="color:#8b9bbd;flex:1;font-size:24px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:16px">{q["name"][:38]}</span>'
                 f'<span style="width:200px;text-align:right">\u20b1{q["price"]:,.2f}</span>'
                 f'<span style="width:180px;text-align:right;font-weight:800;color:{c}">{q["percent_change"]:+.2f}%</span></div>')
    if not rows:
        rows = '<div class="card" style="padding:40px;text-align:center;color:#5b6a8a;font-size:28px">REIT data unavailable today</div>'
    body = f'<div style="margin-top:36px">{rows}</div>'
    return _shell("REIT Board", _fmt_date(s["market_date"]), body, brand)


def dividends_html(snapshot: dict, dividends: list[dict], brand: str) -> str:
    s = snapshot["summary"]
    cards = ""
    shown = [d for d in dividends if d.get("company")][:5] or dividends[:5]
    for d in shown:
        company = d.get("company") or "See PSE Edge disclosure"
        meta = []
        if d.get("rate"):
            meta.append(f'\u20b1{d["rate"]}/share')
        if d.get("ex_date"):
            meta.append(f'Ex: {d["ex_date"]}')
        if d.get("record_date"):
            meta.append(f'Rec: {d["record_date"]}')
        if d.get("payment_date"):
            meta.append(f'Pay: {d["payment_date"]}')
        meta_html = " \u00b7 ".join(meta) if meta else d.get("disclosure_date", "")
        cards += f"""
<div class="card" style="padding:28px 34px;margin-bottom:16px">
  <div style="font-size:31px;font-weight:700">{company}</div>
  <div style="color:{GAIN};font-size:24px;margin-top:6px;font-weight:600">Cash Dividend Declared</div>
  <div style="color:#8b9bbd;font-size:23px;margin-top:10px">{meta_html}</div>
</div>"""
    if not cards:
        cards = '<div class="card" style="padding:48px;text-align:center;color:#5b6a8a;font-size:28px">No cash dividend declarations in the last 3 weeks</div>'
    body = f'<div style="margin-top:34px">{cards}</div>'
    return _shell("Dividend Watch", f"Declarations \u00b7 as of {_fmt_date(s['market_date'])}", body, brand,
                  footer_note="Source: PSE Edge disclosures")


def build_all(snapshot: dict, dividends: list[dict], brand: str) -> dict[str, str]:
    return {
        "market-summary": market_summary_html(snapshot, brand),
        "movers": movers_html(snapshot, brand),
        "sectors": sectors_html(snapshot, brand),
        "reits": reits_html(snapshot, brand),
        "dividends": dividends_html(snapshot, dividends, brand),
    }
