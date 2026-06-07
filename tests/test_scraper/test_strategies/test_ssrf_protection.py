import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from web_core.scraper.strategies.patchright_browser import PatchrightStrategy
from web_core.scraper.strategies.headless import HeadlessStrategy
from web_core.scraper.strategies.captcha import CaptchaStrategy

@pytest.mark.asyncio
async def test_patchright_strategy_ssrf_protection():
    strategy = PatchrightStrategy()
    with pytest.raises(ValueError, match="SSRF blocked"):
        await strategy.fetch("http://127.0.0.1")

@pytest.mark.asyncio
async def test_headless_strategy_ssrf_protection():
    strategy = HeadlessStrategy()
    with pytest.raises(ValueError, match="SSRF blocked"):
        await strategy.fetch("http://127.0.0.1")

@pytest.mark.asyncio
async def test_captcha_strategy_ssrf_protection():
    # Test _solve_cf_turnstile_via_patchright which is called when capsolver_api_key is set
    strategy = CaptchaStrategy(capsolver_api_key="dummy")
    with pytest.raises(ValueError, match="SSRF blocked"):
        await strategy.fetch("http://127.0.0.1")
