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

    def test_default_stealth(self):
        strategy = HeadlessStrategy()
        assert strategy.stealth is True

    def test_stealth_disabled(self):
        strategy = HeadlessStrategy(stealth=False)
        assert strategy.stealth is False

    def test_default_proxy(self):
        strategy = HeadlessStrategy()
        assert strategy.proxy is None

    def test_custom_proxy(self):
        strategy = HeadlessStrategy(proxy="http://proxy.example.com:8080")
        assert strategy.proxy == "http://proxy.example.com:8080"

    def test_build_browser_config_stealth_enabled(self):
        """BrowserConfig should have stealth enabled by default."""
        strategy = HeadlessStrategy()
        with patch("crawl4ai.BrowserConfig") as mock_bc:
            mock_bc.return_value = MagicMock()
            strategy._build_browser_config()

            mock_bc.assert_called_once_with(
                headless=True,
                browser_type="chromium",
                enable_stealth=True,
                user_agent_mode="random",
                verbose=False,
            )

    def test_build_browser_config_stealth_disabled(self):
        """BrowserConfig should respect stealth=False."""
        strategy = HeadlessStrategy(stealth=False)
        with patch("crawl4ai.BrowserConfig") as mock_bc:
            mock_bc.return_value = MagicMock()
            strategy._build_browser_config()

            mock_bc.assert_called_once_with(
                headless=True,
                browser_type="chromium",
                enable_stealth=False,
                user_agent_mode="random",
                verbose=False,
            )

    def test_build_browser_config_with_proxy(self):
        """BrowserConfig should set proxy_config when proxy is provided."""
        strategy = HeadlessStrategy(proxy="http://proxy.example.com:8080")
        with patch("crawl4ai.BrowserConfig") as mock_bc:
            mock_instance = MagicMock()
            mock_bc.return_value = mock_instance
            strategy._build_browser_config()

            assert mock_instance.proxy_config == {"server": "http://proxy.example.com:8080"}

    def test_build_browser_config_without_proxy(self):
        """BrowserConfig should not set proxy_config when proxy is None."""
        strategy = HeadlessStrategy()
        config = strategy._build_browser_config()
        # Real BrowserConfig: proxy_config defaults to None when not set
        assert config.proxy_config is None

    def test_build_crawler_run_config_default_wait_for(self):
        """CrawlerRunConfig should use 'css:body' when wait_for is None."""
        strategy = HeadlessStrategy()
        with patch("crawl4ai.CrawlerRunConfig") as mock_crc:
            mock_crc.return_value = MagicMock()
            strategy._build_crawler_run_config()

            mock_crc.assert_called_once_with(
                wait_for="css:body",
                delay_before_return_html=2.0,
                page_timeout=60000,
                verbose=False,
            )

    def test_build_crawler_run_config_custom_wait_for(self):
        """CrawlerRunConfig should use custom wait_for when provided."""
        strategy = HeadlessStrategy(wait_for="css:.loaded", timeout=45.0)
        with patch("crawl4ai.CrawlerRunConfig") as mock_crc:
            mock_crc.return_value = MagicMock()
            strategy._build_crawler_run_config()

            mock_crc.assert_called_once_with(
                wait_for="css:.loaded",
                delay_before_return_html=2.0,
                page_timeout=45000,
                verbose=False,
            )

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

    async def test_fetch_metadata_includes_stealth_and_proxy(self):
        """Result metadata should include rendered, content_length, wait_for, stealth, and proxy."""
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
        assert result.metadata["stealth"] is True
        assert result.metadata["proxy"] is False

    async def test_fetch_metadata_with_proxy(self):
        """When proxy is configured, metadata should report proxy=True."""
        mock_result = MagicMock()
        mock_result.markdown = "proxied"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(
            proxy="http://proxy.example.com:8080",
            crawler_factory=lambda: mock_crawler,
        )
        result = await strategy.fetch("https://example.com")

        assert result.metadata["proxy"] is True
        assert result.metadata["stealth"] is True

    async def test_fetch_passes_crawler_run_config(self):
        """fetch should pass CrawlerRunConfig to crawler.arun."""
        mock_result = MagicMock()
        mock_result.markdown = "content"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        strategy = HeadlessStrategy(timeout=45.0, wait_for="css:#main", crawler_factory=lambda: mock_crawler)
        await strategy.fetch("https://example.com")

        mock_crawler.arun.assert_called_once()
        call_kwargs = mock_crawler.arun.call_args
        assert call_kwargs.kwargs["url"] == "https://example.com"
        assert "config" in call_kwargs.kwargs

    async def test_fetch_uses_crawl4ai_with_browser_config(self):
        """When no crawler_factory is provided, fetch should use AsyncWebCrawler with BrowserConfig."""
        mock_result = MagicMock()
        mock_result.markdown = "<rendered>"
        mock_result.status_code = 200

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("crawl4ai.AsyncWebCrawler", return_value=mock_crawler) as mock_cls,
            patch("crawl4ai.BrowserConfig") as mock_bc,
            patch("crawl4ai.CrawlerRunConfig") as mock_crc,
        ):
            mock_browser_config = MagicMock(name="browser_config")
            mock_bc.return_value = mock_browser_config
            mock_crawler_run_config = MagicMock(name="crawler_run_config")
            mock_crc.return_value = mock_crawler_run_config

            strategy = HeadlessStrategy()
            result = await strategy.fetch("https://example.com")

            # AsyncWebCrawler should be created with BrowserConfig
            mock_cls.assert_called_once_with(config=mock_browser_config)
            # BrowserConfig should have stealth enabled
            mock_bc.assert_called_once_with(
                headless=True,
                browser_type="chromium",
                enable_stealth=True,
                user_agent_mode="random",
                verbose=False,
            )
            # CrawlerRunConfig should have correct defaults
            mock_crc.assert_called_once_with(
                wait_for="css:body",
                delay_before_return_html=2.0,
                page_timeout=60000,
                verbose=False,
            )
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
