"""Tests for BrowserProvider Protocol."""

from __future__ import annotations

from web_core.browsers.protocol import BrowserProvider


class TestBrowserProvider:
    def test_protocol_structural_typing(self):
        class FakeProvider:
            name = "fake"
            supports_arm64 = True

            async def launch(self, config=None):
                return None

            async def close(self):
                pass

        provider: BrowserProvider = FakeProvider()
        assert provider.name == "fake"
        assert provider.supports_arm64 is True

    def test_isinstance_check(self):
        class FakeProvider:
            name = "fake"
            supports_arm64 = False

            async def launch(self, config=None):
                return None

            async def close(self):
                pass

        assert isinstance(FakeProvider(), BrowserProvider)

    def test_non_conforming_rejected(self):
        class Incomplete:
            name = "incomplete"

        assert not isinstance(Incomplete(), BrowserProvider)
