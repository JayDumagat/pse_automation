"""Config-driven HTTP scraper for HTML and JSON endpoints.

Example YAML::

    name: headlines
    url: https://example.com/news
    item_selector: article.card
    fields:
      title: {selector: h2, attr: text, required: true}
      url: {selector: a, attr: href}

Selectors are CSS selectors for HTML.  For JSON, set ``content_type: json``
and use dot paths in ``item_selector`` and ``path`` (for example
``data.items`` and ``title``).  The config is intentionally data-only: no
arbitrary Python expressions or code execution are supported.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urljoin

import httpx
import yaml
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator


class ScraperField(BaseModel):
    selector: str | None = None
    path: str | None = None
    attr: str = "text"
    regex: str | None = None
    type: Literal["text", "int", "float", "bool", "json"] = "text"
    default: Any = None
    required: bool = False

    @field_validator("attr")
    @classmethod
    def validate_attr(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("attr cannot be blank")
        return value.strip()


class ScraperConfig(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    url: str = Field(min_length=1)
    method: Literal["GET", "POST"] = "GET"
    content_type: Literal["auto", "html", "json"] = "auto"
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    item_selector: str | None = None
    fields: dict[str, ScraperField] = Field(default_factory=dict)
    limit: int | None = Field(default=None, ge=1)
    timeout_seconds: float = Field(default=30, gt=0, le=300)
    retries: int = Field(default=1, ge=0, le=5)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return value

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: dict[str, ScraperField]) -> dict[str, ScraperField]:
        if not value:
            raise ValueError("at least one field is required")
        for name, field in value.items():
            if not field.selector and not field.path:
                raise ValueError(f"field '{name}' needs selector or path")
        return value


def load_scraper_config(path: str | Path) -> ScraperConfig:
    """Load one YAML or JSON scraper definition and validate it."""
    config_path = Path(path)
    if config_path.suffix.lower() in {".yaml", ".yml"}:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    elif config_path.suffix.lower() == ".json":
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        raise ValueError("scraper config must be .yaml, .yml, or .json")
    if not isinstance(raw, dict):
        raise ValueError("scraper config must contain an object")
    return ScraperConfig.model_validate(raw)


def list_scraper_configs(directory: str | Path) -> list[ScraperConfig]:
    config_dir = Path(directory)
    if not config_dir.exists():
        return []
    configs = []
    for path in sorted(config_dir.iterdir()):
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        configs.append(load_scraper_config(path))
    return configs


def _json_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split(".") if path else []:
        if isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(path)
    return current


def _coerce(value: Any, field: ScraperField) -> Any:
    if value is None:
        return field.default
    if field.regex:
        match = re.search(field.regex, str(value), re.S)
        value = match.group(1) if match and match.lastindex else (match.group(0) if match else None)
    if value is None:
        return field.default
    if field.type == "text":
        return str(value).strip()
    if field.type == "int":
        return int(float(str(value).replace(",", "").strip()))
    if field.type == "float":
        return float(str(value).replace(",", "").strip())
    if field.type == "bool":
        return value if isinstance(value, bool) else str(value).strip().lower() in {"1", "true", "yes", "y"}
    if field.type == "json":
        return json.loads(value) if isinstance(value, str) else value
    raise ValueError(f"unsupported field type: {field.type}")


def _extract_html(config: ScraperConfig, body: str, base_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(body, "html.parser")
    roots = soup.select(config.item_selector) if config.item_selector else [soup]
    rows = []
    for root in roots[: config.limit]:
        row = {}
        for name, field in config.fields.items():
            element = root.select_one(field.selector) if field.selector else None
            if element is None:
                value = field.default
            elif field.attr == "text":
                value = element.get_text(" ", strip=True)
            elif field.attr == "html":
                value = str(element)
            else:
                value = element.get(field.attr)
                if field.attr in {"href", "src"} and value:
                    value = urljoin(base_url, value)
            if value is None and field.required:
                raise ValueError(f"required field '{name}' was not found")
            row[name] = _coerce(value, field)
        rows.append(row)
    return rows


def _extract_json(config: ScraperConfig, payload: Any) -> list[dict[str, Any]]:
    items = _json_path(payload, config.item_selector) if config.item_selector else payload
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError("JSON item_selector must resolve to an array or object")
    rows = []
    for item in items[: config.limit]:
        row = {}
        for name, field in config.fields.items():
            try:
                value = _json_path(item, field.path or field.selector or "")
            except (KeyError, IndexError, TypeError):
                value = field.default
            if value is None and field.required:
                raise ValueError(f"required field '{name}' was not found")
            row[name] = _coerce(value, field)
        rows.append(row)
    return rows


async def scrape(config: ScraperConfig, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Fetch and extract records from a config-defined source."""
    owns_client = client is None
    http_client = client or httpx.AsyncClient(follow_redirects=True)
    last_error: Exception | None = None
    try:
        for attempt in range(config.retries + 1):
            try:
                request = http_client.request(
                    config.method, config.url, headers=config.headers, params=config.params,
                    json=config.json_body, timeout=config.timeout_seconds,
                )
                response = await request
                response.raise_for_status()
                content_type = config.content_type
                if content_type == "auto":
                    content_type = "json" if "json" in response.headers.get("content-type", "").lower() else "html"
                records = (_extract_json(config, response.json()) if content_type == "json"
                           else _extract_html(config, response.text, str(response.url)))
                return {
                    "name": config.name, "url": str(response.url), "records": records,
                    "count": len(records), "attempts": attempt + 1,
                }
            except Exception as exc:
                last_error = exc
                if attempt < config.retries:
                    await asyncio.sleep(min(2 ** attempt, 8))
        raise RuntimeError(f"scraper '{config.name}' failed after {config.retries + 1} attempt(s): {last_error}") from last_error
    finally:
        if owns_client:
            await http_client.aclose()


__all__ = [
    "ScraperConfig", "ScraperField", "list_scraper_configs", "load_scraper_config", "scrape",
]
