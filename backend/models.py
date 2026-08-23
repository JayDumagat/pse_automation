"""Pydantic models — deterministic validation for every major data structure."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    symbol: str
    name: str
    price: float = Field(ge=0)
    percent_change: float
    volume: int = Field(ge=0)
    value_traded: float = 0.0


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
    advancers: int = Field(ge=0)
    decliners: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    total_quotes: int = Field(ge=0)


class DividendItem(BaseModel):
    company: str = ""
    title: str
    disclosure_date: str
    edge_no: str
    ex_date: Optional[str] = None
    record_date: Optional[str] = None
    payment_date: Optional[str] = None
    rate: Optional[str] = None


class SettingsModel(BaseModel):
    llm_provider: str = "openai"
    llm_model: str = "gpt-5.4-mini"
    schedule_enabled: bool = False
    schedule_time: str = "17:00"
    timezone: str = "Asia/Manila"
    reit_tickers: list[str] = ["AREIT", "RCR", "MREIT", "CREIT", "FILRT", "DDMPR", "VREIT", "PREIT"]
    brand_name: str = "PSE Daily Pulse"


PLATFORMS = ["instagram", "facebook", "linkedin", "x"]

GRAPHIC_TYPES = ["market-summary", "movers", "sectors", "reits", "dividends"]

STAGES = ["fetch", "validate", "compute", "store", "graphics", "captions", "qa", "ready"]

AVAILABLE_MODELS = {
    "openai": ["gpt-5.4", "gpt-5.4-mini", "gpt-5.2", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini"],
    "anthropic": ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-5-20251101"],
    "gemini": ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.1-pro-preview"],
}
