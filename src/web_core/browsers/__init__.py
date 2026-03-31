"""Browser providers for stealth web automation."""

from web_core.browsers.patchright import PatchrightProvider
from web_core.browsers.protocol import BrowserProvider

__all__ = ["BrowserProvider", "PatchrightProvider"]
