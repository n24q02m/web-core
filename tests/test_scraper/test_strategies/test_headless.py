"""Tests for HeadlessStrategy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from web_core.scraper.strategies.headless import HeadlessStrategy


class TestHeadlessStrategy:
    """Test Crawl4AI headless scraping strategy."""

    def test_name(self):
        strategy = HeadlessStrategy()
        assert strategy.name == "headless"

    def test_default_timeout(self):
        strategy = HeadlessStrategy()
        assert strategy.timeout == 60.0

    def test_custom_timeout(self):
        strategy = HeadlessStrategy(timeout=120.0)
        assert strategy.timeout == 120.0

    def test_default_wait_for(self):
        strategy = HeadlessStrategy()
        assert strategy.wait_for is None

    def test_custom_wait_for(self):
        strategy = HeadlessStrategy(wait_for="css:.content")
        assert strategy.wait_for == "css:.content"

    async def test_fetch_success_with_crawler_factory(self):
        """fetch should use crawler_factory and return markdown content."""
        mock_result = MagicMock()
        mock_result.markdown = "# Hello World\n\nThis is rendered content."
        mock_result.html = "<html><body><h1>Hello World</h1></body></html>"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.content == "# Hello World\n\nThis is rendered content."
        assert result.url == "https://example.com"
        assert result.strategy == "headless"
        assert result.status_code == 200

    async def test_fetch_prefers_markdown_over_html(self):
        """When markdown is available, it should be preferred over html."""
        mock_result = MagicMock()
        mock_result.markdown = "markdown content"
        mock_result.html = "<html>html content</html>"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.content == "markdown content"

    async def test_fetch_falls_back_to_html(self):
        """When markdown is empty, fetch should fall back to html."""
        mock_result = MagicMock()
        mock_result.markdown = ""
        mock_result.html = "<html>html content</html>"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.content == "<html>html content</html>"

    async def test_fetch_empty_content(self):
        """When both markdown and html are empty, content should be empty."""
        mock_result = MagicMock()
        mock_result.markdown = ""
        mock_result.html = ""
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.content == ""

    async def test_fetch_metadata(self):
        """Result metadata should include rendered, content_length, and wait_for."""
        mock_result = MagicMock()
        mock_result.markdown = "hello"
        mock_result.html = ""
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(wait_for="css:.loaded", crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.metadata["rendered"] is True
        assert result.metadata["content_length"] == 5
        assert result.metadata["wait_for"] == "css:.loaded"

    async def test_fetch_passes_timeout_and_wait_for(self):
        """fetch should pass timeout and wait_for to crawler.arun."""
        mock_result = MagicMock()
        mock_result.markdown = "content"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(timeout=45.0, wait_for="css:#main", crawler_factory=lambda: mock_crawler)
        await strategy.fetch("https://example.com")

        mock_crawler.arun.assert_called_once_with(
            url="https://example.com",
            timeout=45.0,
            wait_for="css:#main",
        )

    async def test_fetch_uses_crawl4ai_when_no_factory(self):
        """When no crawler_factory is provided, fetch should import AsyncWebCrawler."""
        mock_result = MagicMock()
        mock_result.markdown = "<rendered>"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)

        with patch("crawl4ai.AsyncWebCrawler", return_value=mock_crawler) as mock_cls:
            strategy = HeadlessStrategy()
            result = await strategy.fetch("https://example.com")

            mock_cls.assert_called_once()
            assert result.content == "<rendered>"

    async def test_fetch_failure_propagates(self):
        """Errors from the crawler should propagate to the caller."""
        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(side_effect=TimeoutError("Browser timed out"))

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        with pytest.raises(TimeoutError, match="Browser timed out"):
            await strategy.fetch("https://example.com")

    async def test_fetch_missing_status_code(self):
        """When result has no status_code attr, default to 200."""
        mock_result = MagicMock(spec=[])  # empty spec = no attributes
        mock_result.markdown = "content"

        # Remove status_code so getattr falls back
        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.status_code == 200

    async def test_fetch_none_markdown_falls_back_to_html(self):
        """When markdown is None (not just empty), fall back to html."""
        mock_result = MagicMock()
        mock_result.markdown = None
        mock_result.html = "<html>fallback</html>"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(crawler_factory=lambda: mock_crawler)
        result = await strategy.fetch("https://example.com")

        assert result.content == "<html>fallback</html>"
