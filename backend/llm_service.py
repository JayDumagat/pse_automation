"""Direct OpenAI caption generation using validated market numbers only."""
import json
import logging
import os
import re

from openai import AsyncOpenAI

logger = logging.getLogger("llm")

SYSTEM_MESSAGE = (
    "You are the social media copywriter for a Philippine stock market daily brand. "
    "You write engaging, accurate captions. STRICT RULES: use ONLY the exact numbers provided "
    "in the prompt — never invent, recompute, or round differently. No financial advice. "
    "Philippine audience, English with light Taglish acceptable on Instagram/X only."
)


def _context_block(snapshot: dict) -> str:
    s = snapshot["summary"]
    gainers = ", ".join(f"{q['symbol']} {q['percent_change']:+.2f}%" for q in snapshot["gainers"][:3]) or "none"
    losers = ", ".join(f"{q['symbol']} {q['percent_change']:+.2f}%" for q in snapshot["losers"][:3]) or "none"
    active = snapshot["actives"][0] if snapshot["actives"] else None
    sectors = sorted(snapshot["sectors"], key=lambda x: -x["change_percent"])
    best = sectors[0] if sectors else None
    worst = sectors[-1] if sectors else None
    lines = [
        f"Market date: {s['market_date']}",
        f"PSEi close: {s['psei_value']:,.2f} ({s['change_points']:+,.2f} pts, {s['change_percent']:+.2f}%)",
        f"Breadth: {s['advancers']} advancers, {s['decliners']} decliners, {s['unchanged']} unchanged",
        f"Value turnover: PHP {s.get('value_turnover', s['approx_value_turnover']):,.0f}",
        f"Total market volume: {s['total_volume']:,}",
        f"Total market trades: {s['total_trades']:,}" if s.get("total_trades") is not None else "Total market trades: unavailable",
        f"Top gainers: {gainers}",
        f"Top losers: {losers}",
    ]
    if active:
        lines.append(f"Most active by value: {active['symbol']} (PHP {active['value_traded']:,.0f})")
    if best and worst:
        lines.append(f"Best sector: {best['name']} {best['change_percent']:+.2f}% | Worst sector: {worst['name']} {worst['change_percent']:+.2f}%")
    if snapshot.get("explanation"):
        lines.append(f"Deterministic market explanation: {snapshot['explanation']}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if match:
        text = match.group(1)
    else:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            text = match.group(0)
    return json.loads(text)


def _openai_client(provider: str) -> AsyncOpenAI:
    if provider != "openai":
        raise RuntimeError("Direct API caption generation currently supports only the openai provider")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=api_key)


async def _complete(client: AsyncOpenAI, model: str, prompt: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


async def generate_captions(snapshot: dict, provider: str, model: str) -> dict[str, str]:
    """One direct OpenAI call returns captions for all four platforms as JSON."""
    prompt = f"""Here is today's VALIDATED Philippine stock market data:

{_context_block(snapshot)}

Write one caption per platform. Return ONLY valid JSON exactly in this shape (no extra keys, no markdown):
{{"instagram": "...", "facebook": "...", "linkedin": "...", "x": "..."}}

Platform style:
- instagram: energetic, 60-100 words, line breaks allowed, end with 4-6 hashtags including #PSEi #PhilippineStocks
- facebook: conversational, 50-90 words, 2-3 hashtags
- linkedin: professional market recap tone, 70-110 words, no emojis, 3 hashtags
- x: punchy, MAX 260 characters total including 2 hashtags"""
    client = _openai_client(provider)
    try:
        data = _extract_json(await _complete(client, model, prompt))
        return {platform: str(data.get(platform, "")).strip() for platform in ["instagram", "facebook", "linkedin", "x"]}
    finally:
        await client.close()


async def regenerate_caption(snapshot: dict, platform: str, provider: str, model: str) -> str:
    styles = {
        "instagram": "energetic, 60-100 words, line breaks allowed, end with 4-6 hashtags including #PSEi #PhilippineStocks",
        "facebook": "conversational, 50-90 words, 2-3 hashtags",
        "linkedin": "professional market recap tone, 70-110 words, no emojis, 3 hashtags",
        "x": "punchy, MAX 260 characters total including 2 hashtags",
    }
    if platform not in styles:
        raise ValueError(f"Unsupported caption platform: {platform}")
    prompt = f"""Here is today's VALIDATED Philippine stock market data:

{_context_block(snapshot)}

Write ONE {platform} caption. Style: {styles[platform]}.
Return ONLY the caption text — no JSON, no quotes, no preamble."""
    client = _openai_client(provider)
    try:
        return (await _complete(client, model, prompt)).strip().strip('"')
    finally:
        await client.close()
