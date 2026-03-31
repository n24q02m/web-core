"""Scraping strategies."""

from web_core.scraper.strategies.api_direct import APIDirectStrategy
from web_core.scraper.strategies.basic_http import BasicHTTPStrategy
from web_core.scraper.strategies.tls_spoof import TLSSpoofStrategy

__all__ = ["APIDirectStrategy", "BasicHTTPStrategy", "TLSSpoofStrategy"]
