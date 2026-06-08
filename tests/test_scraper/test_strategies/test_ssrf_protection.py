from unittest.mock import patch

import pytest

from web_core.scraper.strategies.captcha import CaptchaStrategy
from web_core.scraper.strategies.headless import HeadlessStrategy
from web_core.scraper.strategies.patchright_browser import PatchrightStrategy


@pytest.mark.asyncio
async def test_patchright_strategy_blocks_ssrf():
    strategy = PatchrightStrategy()
    with (
        patch("web_core.scraper.strategies.patchright_browser.is_safe_url", return_value=False),
        pytest.raises(ValueError, match="SSRF blocked"),
    ):
        await strategy.fetch("http://127.0.0.1")


@pytest.mark.asyncio
async def test_captcha_strategy_blocks_ssrf():
    strategy = CaptchaStrategy(capsolver_api_key="key")
    with (
        patch("web_core.scraper.strategies.captcha.is_safe_url", return_value=False),
        pytest.raises(ValueError, match="SSRF blocked"),
    ):
        await strategy.fetch("http://127.0.0.1")


@pytest.mark.asyncio
async def test_headless_strategy_blocks_ssrf():
    strategy = HeadlessStrategy()
    with (
        patch("web_core.scraper.strategies.headless.is_safe_url", return_value=False),
        pytest.raises(ValueError, match="SSRF blocked"),
    ):
        await strategy.fetch("http://127.0.0.1")
