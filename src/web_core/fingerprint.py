"""Consistent browser identity profiles for a scraping session."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class FingerprintProfile:
    """Browser and TLS identity selected once for a domain."""

    user_agent: str
    platform: str
    viewport_width: int
    viewport_height: int
    locale: str
    timezone_id: str
    webgl_vendor: str
    webgl_renderer: str
    impersonate: str = "chrome131"

    @classmethod
    def for_domain(cls, domain: str) -> FingerprintProfile:
        """Return the stable in-process profile for *domain*."""
        return _profile_for_domain(domain)


@lru_cache(maxsize=256)
def _profile_for_domain(domain: str) -> FingerprintProfile:
    """Generate a domain-seeded profile from BrowserForge data."""
    from browserforge.fingerprints import FingerprintGenerator

    digest = hashlib.sha256(domain.encode("utf-8")).digest()
    fingerprint = FingerprintGenerator().generate(browser="chrome", os="windows", device="desktop")
    navigator = fingerprint.navigator
    video_card = fingerprint.videoCard
    user_agent = re.sub(r"Chrome/\d+(?:\.\d+)*", "Chrome/131.0.0.0", navigator.userAgent)
    viewports = ((1280, 720), (1366, 768), (1440, 900), (1536, 864))
    locales = ("en-US", "en-GB", "de-DE", "fr-FR")
    timezones = ("UTC", "Europe/London", "Europe/Berlin", "America/New_York")
    viewport_width, viewport_height = viewports[digest[0] % len(viewports)]
    return FingerprintProfile(
        user_agent=user_agent,
        platform=navigator.platform,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        locale=locales[digest[1] % len(locales)],
        timezone_id=timezones[digest[2] % len(timezones)],
        webgl_vendor=video_card.vendor,
        webgl_renderer=video_card.renderer,
    )
