"""LLM caption generation via emergentintegrations — provider/model switchable at call time.
LLM receives VALIDATED numbers only; it never calculates.
"""
import json
import logging
import os
import re
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage

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
        f"Approx value turnover: PHP {s['approx_value_turnover']:,.0f}",
        f"Top gainers: {gainers}",
        f"Top losers: {losers}",
    ]
    if active:
        lines.append(f"Most active by value: {active['symbol']} (PHP {active['value_traded']:,.0f})")
    if best and worst:
        lines.append(f"Best sector: {best['name']} {best['change_percent']:+.2f}% | Worst sector: {worst['name']} {worst['change_percent']:+.2f}%")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    else:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            text = m.group(0)
    return json.loads(text)


async def generate_captions(snapshot: dict, provider: str, model: str) -> dict[str, str]:
    """One LLM call -> captions for all 4 platforms as JSON."""
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(api_key=api_key, session_id=f"captions-{uuid.uuid4().hex[:8]}",
                   system_message=SYSTEM_MESSAGE).with_model(provider, model)
    prompt = f"""Here is today's VALIDATED Philippine stock market data:

{_context_block(snapshot)}

Write one caption per platform. Return ONLY valid JSON exactly in this shape (no extra keys, no markdown):
{{"instagram": "...", "facebook": "...", "linkedin": "...", "x": "..."}}

Platform style:
- instagram: energetic, 60-100 words, line breaks allowed, end with 4-6 hashtags including #PSEi #PhilippineStocks
- facebook: conversational, 50-90 words, 2-3 hashtags
- linkedin: professional market recap tone, 70-110 words, no emojis, 3 hashtags
- x: punchy, MAX 260 characters total including 2 hashtags"""
    resp = await chat.send_message(UserMessage(text=prompt))
    data = _extract_json(str(resp))
    out = {}
    for platform in ["instagram", "facebook", "linkedin", "x"]:
        out[platform] = str(data.get(platform, "")).strip()
    return out


async def regenerate_caption(snapshot: dict, platform: str, provider: str, model: str) -> str:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(api_key=api_key, session_id=f"caption-{platform}-{uuid.uuid4().hex[:8]}",
                   system_message=SYSTEM_MESSAGE).with_model(provider, model)
    styles = {
        "instagram": "energetic, 60-100 words, line breaks allowed, end with 4-6 hashtags including #PSEi #PhilippineStocks",
        "facebook": "conversational, 50-90 words, 2-3 hashtags",
        "linkedin": "professional market recap tone, 70-110 words, no emojis, 3 hashtags",
        "x": "punchy, MAX 260 characters total including 2 hashtags",
    }
    prompt = f"""Here is today's VALIDATED Philippine stock market data:

{_context_block(snapshot)}

Write ONE {platform} caption. Style: {styles[platform]}.
Return ONLY the caption text — no JSON, no quotes, no preamble."""
    resp = await chat.send_message(UserMessage(text=prompt))
    return str(resp).strip().strip('"')
