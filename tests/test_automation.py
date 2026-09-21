import httpx
from backend.configurable_scraper import ScraperConfig, scrape
from backend.orchestrator import AutomationOrchestrator, Stage, WorkflowContext


def test_html_scraper_extracts_and_coerces_fields():
    config = ScraperConfig.model_validate({
        "name": "products",
        "url": "https://example.test/products",
        "item_selector": ".product",
        "fields": {
            "name": {"selector": "h2", "required": True},
            "price": {"selector": ".price", "type": "float", "regex": r"([0-9.]+)"},
            "url": {"selector": "a", "attr": "href"},
        },
    })

    async def handler(request: httpx.Request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<article class="product"><h2>Widget</h2><span class="price">$12.50</span><a href="/w">Open</a></article>',
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await scrape(config, client)

    import asyncio
    result = asyncio.run(run())
    assert result["records"] == [{"name": "Widget", "price": 12.5, "url": "https://example.test/w"}]


def test_json_scraper_and_orchestrator():
    config = ScraperConfig.model_validate({
        "name": "items",
        "url": "https://example.test/items",
        "content_type": "json",
        "item_selector": "data.items",
        "fields": {"title": {"path": "title", "required": True}, "rank": {"path": "rank", "type": "int"}},
    })

    async def handler(request: httpx.Request):
        return httpx.Response(200, json={"data": {"items": [{"title": "A", "rank": "1"}]}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            scraped = await scrape(config, client)
        context = WorkflowContext({"scraped": scraped})
        workflow = AutomationOrchestrator([
            Stage("fetch", lambda ctx: ctx.values["scraped"]),
            Stage("transform", lambda ctx: {"title": ctx.values["fetch"]["records"][0]["title"]}, depends_on=("fetch",)),
        ])
        return await workflow.run(context)

    import asyncio
    result = asyncio.run(run())
    assert result.status == "completed"
    assert result.values["transform"] == {"title": "A"}
