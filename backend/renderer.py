"""Playwright HTML -> PNG renderer for social graphics (1080x1350)."""
import logging
import os
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger("renderer")

STORAGE_DIR = Path(__file__).parent / "storage" / "graphics"


async def render_graphics(run_id: str, html_map: dict[str, str]) -> list[dict]:
    """Render each HTML template to a PNG. Returns metadata list."""
    out_dir = STORAGE_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        for gtype, html in html_map.items():
            try:
                path = out_dir / f"{gtype}.png"
                try:
                    await page.set_content(html, wait_until="networkidle", timeout=20000)
                except Exception:
                    # fonts CDN slow/unreachable -> render with fallback fonts
                    await page.set_content(html, wait_until="load", timeout=15000)
                await page.screenshot(path=str(path), full_page=False)
                size = os.path.getsize(path)
                results.append({
                    "run_id": run_id, "type": gtype, "filename": f"{gtype}.png",
                    "width": 1080, "height": 1350, "size_bytes": size, "approved": False,
                })
                logger.info(f"rendered {gtype} ({size//1024} KB)")
            except Exception as e:
                logger.error(f"render failed for {gtype}: {e}")
        await browser.close()
    return results


def graphic_path(run_id: str, gtype: str) -> Path:
    return STORAGE_DIR / run_id / f"{gtype}.png"
