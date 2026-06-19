"""WS-1: the agent escalates past an under-rendered JS shell to a headless leg.

Covers the root-cause fix: a 200-OK SPA shell ("Loading…" + scripts, no visible
content) must FAIL validation so the graph advances to a heavier strategy,
instead of extracting the empty shell.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from web_core.scraper.agent import ScrapingAgent
from web_core.scraper.base import BaseStrategy, ScrapingResult

# A 200-OK SPA shell: empty mount root + scripts + a Loading marker.
SHELL_HTML = (
    "<html><head><title>SPA</title></head><body>"
    "<div id='root'></div>"
    "<script src='/static/app.js'></script>"
    "<script>window.__INIT__ = {};</script>"
    "<p>Loading…</p></body></html>"
)

# A fully-rendered page with real visible content (well over the threshold).
RENDERED_HTML = "<html><body><article>" + "Real rendered article content. " * 8 + "</article></body></html>"

# Short but complete, no scripts: > min_content_length raw, > 64 visible text.
TINY_COMPLETE_JSON = '{"answer": "' + "x" * 120 + '"}'


class _Stub(BaseStrategy):
    """Strategy returning a fixed body, tracking how often it was called."""

    def __init__(self, name: str, content: str, status_code: int = 200):
        self.name = name
        self._content = content
        self._status_code = status_code
        self.call_count = 0

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        self.call_count += 1
        return ScrapingResult(content=self._content, url=url, strategy=self.name, status_code=self._status_code)


class TestUnderRenderedEscalation:
    async def test_shell_skips_inference_and_escalates_to_headless(self):
        """An under-rendered shell must escalate WITHOUT invoking LLM inference."""
        shell = _Stub("basic_http", SHELL_HTML)
        headless = _Stub("headless", RENDERED_HTML)
        agent = ScrapingAgent(strategies={"basic_http": shell, "headless": headless})

        with patch("web_core.scraper.agent.infer_selectors_with_llm", new_callable=AsyncMock) as mock_llm:
            result = await agent.scrape("https://spa.example.com")

        assert "Real rendered article" in result
        assert shell.call_count == 1
        assert headless.call_count == 1
        # Selector inference is pointless on an empty DOM -> must be skipped.
        mock_llm.assert_not_called()

    async def test_fully_rendered_page_validates_without_escalation(self):
        rendered = _Stub("basic_http", RENDERED_HTML)
        agent = ScrapingAgent(strategies={"basic_http": rendered})

        result = await agent.scrape("https://example.com")

        assert "Real rendered article" in result
        assert rendered.call_count == 1

    async def test_short_complete_no_script_not_false_escalated(self):
        """A complete-but-short, script-free body (API JSON) must not escalate."""
        page = _Stub("basic_http", TINY_COMPLETE_JSON)
        agent = ScrapingAgent(strategies={"basic_http": page})

        result = await agent.scrape("https://api.example.com")

        assert result == TINY_COMPLETE_JSON
        assert page.call_count == 1


class TestValidateNodeUnderRendered:
    async def test_validate_node_flags_shell(self):
        agent = ScrapingAgent()
        state = {"content": SHELL_HTML, "status_code": 200, "metadata": {"last_strategy": "basic_http"}}

        new_state = await agent._validate_node(state)

        assert new_state["success"] is False
        assert new_state["under_rendered"] is True
        assert any("under-rendered" in e for e in new_state["errors"])

    async def test_validate_node_passes_rendered(self):
        agent = ScrapingAgent()
        state = {"content": RENDERED_HTML, "status_code": 200, "metadata": {}}

        new_state = await agent._validate_node(state)

        assert new_state["success"] is True
        assert new_state["under_rendered"] is False

    def test_route_after_validate_under_rendered_goes_to_escalate(self):
        agent = ScrapingAgent()
        state = {"success": False, "under_rendered": True, "content": SHELL_HTML}

        assert agent._route_after_validate(state) == "escalate"
