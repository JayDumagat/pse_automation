"""Pydantic models and maintained market-universe defaults."""
from typing import Optional

from pydantic import BaseModel, Field


# The PSE reviews the PSEi semi-annually.  This is the basket effective
# 2026-08-03; keeping the effective date beside the list prevents a future
# rebalance from silently changing historical snapshots.
PSEI_MEMBERSHIP_AS_OF = "2026-08-03"
PSEI_TICKERS = [
    "AC", "DMC", "MONDE", "ACEN", "EMI", "PGOLD", "AEV", "GLO", "PLUS", "ALI",
    "GTCAP", "RCR", "AREIT", "ICT", "SCC", "BDO", "JFC", "SM", "BPI", "JGS",
    "SMC", "CBC", "LTG", "SMPH", "CNPF", "MBT", "TEL", "MYNLD", "MER", "URC",
]
REIT_TICKERS = ["RCR", "MREIT", "AREIT", "FILRT", "DDMPR", "CREIT", "PREIT", "VREIT"]
DIVY_TICKERS = ["RCR", "SCC", "LTG", "MER", "GLO", "TEL", "MBT", "DMC"]


class StockQuote(BaseModel):
    symbol: str
    name: str
    price: float = Field(ge=0)
    percent_change: float
    volume: int = Field(ge=0)
    value_traded: float = 0.0
    # Phisix and the fallback quote feeds do not publish per-symbol trade
    # counts.  Keep this nullable so the app never presents volume as trades.
    trades: Optional[int] = Field(default=None, ge=0)


class IndexQuote(BaseModel):
    symbol: str
    name: str
    value: float
    previous_close: float
    change_points: float
    change_percent: float
    day_high: Optional[float] = None
    day_low: Optional[float] = None


class MarketSummary(BaseModel):
    market_date: str
    psei_value: float
    change_points: float
    change_percent: float
    approx_value_turnover: float
    value_turnover: float = 0.0
    advancers: int = Field(ge=0)
    decliners: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    total_quotes: int = Field(ge=0)
    total_volume: int = Field(default=0, ge=0)
    total_trades: Optional[int] = Field(default=None, ge=0)
    value_turnover_source: str = "derived"


class DividendItem(BaseModel):
    symbol: str = ""
    company: str = ""
    title: str
    disclosure_date: str
    edge_no: str
    ex_date: Optional[str] = None
    record_date: Optional[str] = None
    payment_date: Optional[str] = None
    rate: Optional[str] = None
    dividend_per_share: Optional[float] = Field(default=None, ge=0)


class SettingsModel(BaseModel):
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    schedule_enabled: bool = False
    schedule_time: str = "17:00"
    timezone: str = "Asia/Manila"
    reit_tickers: list[str] = Field(default_factory=lambda: list(REIT_TICKERS))
    divy_tickers: list[str] = Field(default_factory=lambda: list(DIVY_TICKERS))
    psei_tickers: list[str] = Field(default_factory=lambda: list(PSEI_TICKERS))
    brand_name: str = "PSE Daily Pulse"


PLATFORMS = ["instagram", "facebook", "linkedin", "x"]

GRAPHIC_TYPES = ["market-summary", "movers", "sectors", "reits", "dividends"]

STAGES = ["fetch", "validate", "compute", "store", "graphics", "captions", "qa", "ready"]

AVAILABLE_MODELS = {
    "openai": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-5-mini", "gpt-5.4-mini"],
}
