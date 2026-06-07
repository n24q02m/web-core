"""Tests for HeadlessStrategy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.strategies.headless import HeadlessStrategy


@pytest.fixture(autouse=True)
def mock_is_safe_url():
    with patch("web_core.scraper.strategies.headless.is_safe_url", return_value=True):
        yield


class TestHeadlessStrategy:
    """Test Crawl4AI headless scraping strategy."""

    def test_name(self):
        strategy = HeadlessStrategy()
        assert strategy.name == "headless"

    def test_default_timeout(self):
        strategy = HeadlessStrategy()
        assert strategy.timeout == 60.0

    def test_build_browser_config_stealth(self):
        strategy = HeadlessStrategy(stealth=True)
        config = strategy._build_browser_config()
        assert config.enable_stealth is True
        assert config.user_agent_mode == "random"

    def test_build_browser_config_proxy(self):
        strategy = HeadlessStrategy(proxy="http://proxy:8080")
        config = strategy._build_browser_config()
        assert config.proxy_config == {"server": "http://proxy:8080"}

    def test_build_run_config_custom_wait(self):
        strategy = HeadlessStrategy(wait_for="css:.main")
        config = strategy._build_crawler_run_config()
        assert config.wait_for == "css:.main"
        assert config.page_timeout == 60000

    @pytest.mark.asyncio
    async def test_fetch_success(self):
        mock_result = MagicMock()
        mock_result.markdown = "# Hello"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = mock_result

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.content == "# Hello"
        assert result.status_code == 200
        assert result.strategy == "headless"
        assert result.metadata["rendered"] is True

    @pytest.mark.asyncio
    async def test_fetch_with_context_manager(self):
        """Test fetch when it instantiates AsyncWebCrawler (lines 71-74)."""
        mock_result = MagicMock()
        mock_result.markdown = "<html>test</html>"
        mock_result.status_code = 200

        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.arun.return_value = mock_result

        with patch("crawl4ai.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance

            strategy = HeadlessStrategy()
            result = await strategy.fetch("https://example.com")

        assert result.content == "<html>test</html>"
        assert result.status_code == 200
        mock_crawler_instance.arun.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_fallback_to_html(self):
        mock_result = MagicMock()
        mock_result.markdown = None
        mock_result.html = "<html>Hello</html>"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = mock_result

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.content == "<html>Hello</html>"

    @pytest.mark.asyncio
    async def test_fetch_empty_result(self):
        mock_result = MagicMock()
        mock_result.markdown = None
        mock_result.html = None
        mock_result.status_code = 500

        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = mock_result

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.content == ""
        assert result.status_code == 500
