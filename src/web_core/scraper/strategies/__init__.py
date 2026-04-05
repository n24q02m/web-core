"""Scraping strategies."""

from web_core.scraper.strategies.api_direct import APIDirectStrategy
from web_core.scraper.strategies.basic_http import BasicHTTPStrategy
from web_core.scraper.strategies.captcha import CaptchaStrategy
from web_core.scraper.strategies.headless import HeadlessStrategy
from web_core.scraper.strategies.patchright_browser import PatchrightStrategy
from web_core.scraper.strategies.tls_spoof import TLSSpoofStrategy

__all__ = [
    "APIDirectStrategy",
    "BasicHTTPStrategy",
    "CaptchaStrategy",
    "HeadlessStrategy",
    "PatchrightStrategy",
    "TLSSpoofStrategy",
]
