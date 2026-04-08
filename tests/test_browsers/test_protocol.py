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

    async def test_protocol_launch_and_close_callable(self):
        """Verify that a conforming provider's launch and close can be called."""

        class FakeProvider:
            name = "test"
            supports_arm64 = True
            launched = False
            closed = False

            async def launch(self, config=None):
                self.launched = True
                return {"browser": True}

            async def close(self):
                self.closed = True

        provider = FakeProvider()
        result = await provider.launch()
        assert result == {"browser": True}
        assert provider.launched is True

        await provider.close()
        assert provider.closed is True

    async def test_protocol_launch_with_config(self):
        """Launch with config parameter."""

        class FakeProvider:
            name = "configurable"
            supports_arm64 = False
            _config = None

            async def launch(self, config=None):
                self._config = config
                return "browser-instance"

            async def close(self):
                pass

        provider: BrowserProvider = FakeProvider()
        result = await provider.launch(config={"headless": True})
        assert result == "browser-instance"
