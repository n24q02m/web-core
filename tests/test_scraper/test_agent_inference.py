from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from web_core.scraper.agent import ScrapingAgent
from web_core.scraper.base import BaseStrategy, ScrapingResult
from web_core.scraper.state import ScrapingState


class MockStrategy(BaseStrategy):
    """Configurable mock strategy for testing."""

    def __init__(
        self,
        name: str = "mock",
        should_fail: bool = False,
        content: str = "<html>mock content that is long enough for validation</html>" + "x" * 100,
        status_code: int = 200,
    ):
        self.name = name
        self._should_fail = should_fail
        self._content = content
        self._status_code = status_code
        self.call_count = 0

    async def fetch(self, url: str, selectors: dict[str, str] | None = None) -> ScrapingResult:
        self.call_count += 1
        if self._should_fail:
            raise RuntimeError(f"Mock failure from {self.name}")
        return ScrapingResult(
            content=self._content,
            url=url,
            strategy=self.name,
            status_code=self._status_code,
        )


class TestScrapingAgentInference:
    """Test selector inference logic in ScrapingAgent."""

    async def test_infer_selectors_node_domain_config(self):
        """Node should use domain config if available and no existing selectors."""
        agent = ScrapingAgent()
        state: ScrapingState = {
            "url": "https://example.com",
            "content": "<html>some content</html>",
            "selectors": {},
            "inferred_selectors": {},
        }

        domain_selectors = {"content": "#main"}
        with patch("web_core.scraper.agent.get_domain_selectors", return_value=domain_selectors):
            new_state = await agent._infer_selectors_node(state)

        assert new_state["selectors"] == domain_selectors
        assert new_state["inferred_selectors"] == domain_selectors
        assert new_state["selector_inference_attempted"] is True

    async def test_infer_selectors_node_llm(self):
        """Node should use LLM if domain config is not available or selectors exist."""
        agent = ScrapingAgent()
        state: ScrapingState = {
            "url": "https://unknown.com",
            "content": "<html>some content</html>",
            "selectors": {"existing": "val"},
            "inferred_selectors": {},
        }

        llm_selectors = {"content": ".article"}

        with (
            patch("web_core.scraper.agent.get_domain_selectors", return_value={"domain": "selectors"}),
            patch(
                "web_core.scraper.agent.infer_selectors_with_llm", new_callable=AsyncMock, return_value=llm_selectors
            ),
        ):
            new_state = await agent._infer_selectors_node(state)

        assert new_state["selectors"] == {"existing": "val", "content": ".article"}
        assert new_state["inferred_selectors"] == llm_selectors
        assert new_state["selector_inference_attempted"] is True

    async def test_infer_selectors_node_llm_empty_result(self):
        """Node should mark attempted even if LLM returns nothing."""
        agent = ScrapingAgent()
        state: ScrapingState = {
            "url": "https://unknown.com",
            "content": "<html>some content</html>",
            "selectors": {},
            "inferred_selectors": {},
        }

        with (
            patch("web_core.scraper.agent.get_domain_selectors", return_value=None),
            patch("web_core.scraper.agent.infer_selectors_with_llm", new_callable=AsyncMock, return_value={}),
        ):
            new_state = await agent._infer_selectors_node(state)

        assert new_state["selector_inference_attempted"] is True
        assert new_state.get("inferred_selectors") == {}

    async def test_infer_selectors_node_failure_graceful(self):
        """Node should handle LLM failure gracefully."""
        agent = ScrapingAgent()
        state: ScrapingState = {
            "url": "https://unknown.com",
            "content": "<html>some content</html>",
            "selectors": {},
            "inferred_selectors": {},
        }

        with (
            patch("web_core.scraper.agent.get_domain_selectors", return_value=None),
            patch("web_core.scraper.agent.infer_selectors_with_llm", side_effect=Exception("LLM Down")),
        ):
            new_state = await agent._infer_selectors_node(state)

        assert new_state["selector_inference_attempted"] is True
        assert new_state.get("inferred_selectors") == {}

    async def test_workflow_triggers_inference(self):
        """Workflow should trigger inference when validation fails on content length."""
        short_content = "<html>" + "a" * 60 + "</html>"
        strategy = MockStrategy(name="short")

        agent = ScrapingAgent(strategies={"short": strategy}, min_content_length=150, enable_selector_inference=True)

        llm_selectors = {"content": "#real-content"}

        async def fetch_side_effect(url, selectors=None):
            if selectors and selectors.get("content") == "#real-content":
                return ScrapingResult(content="A" * 200, url=url, strategy="short", status_code=200)
            return ScrapingResult(content=short_content, url=url, strategy="short", status_code=200)

        strategy.fetch = AsyncMock(side_effect=fetch_side_effect)

        with (
            patch("web_core.scraper.agent.get_domain_selectors", return_value=None),
            patch(
                "web_core.scraper.agent.infer_selectors_with_llm", new_callable=AsyncMock, return_value=llm_selectors
            ),
        ):
            content = await agent.scrape("https://example.com")

        assert content == "A" * 200
        assert strategy.fetch.call_count == 2

    async def test_workflow_inference_disabled(self):
        """Workflow should NOT trigger inference if disabled."""
        short_content = "<html>" + "a" * 60 + "</html>"
        strategy = MockStrategy(name="short", content=short_content)

        agent = ScrapingAgent(strategies={"short": strategy}, min_content_length=150, enable_selector_inference=False)

        from web_core.scraper.state import ScrapingError

        with pytest.raises(ScrapingError):
            await agent.scrape("https://example.com")

        assert strategy.call_count == 1
