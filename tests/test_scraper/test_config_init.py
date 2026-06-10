from web_core.scraper import ScraperConfig, ScrapingAgent


class TestScrapingAgentConfig:
    """Tests for ScrapingAgent configuration and initialization."""

    def test_init_with_config_object(self):
        """Should correctly use the provided ScraperConfig object."""
        config = ScraperConfig(
            max_retries=10,
            min_content_length=500,
            enable_selector_inference=False,
            respect_robots=False,
        )
        agent = ScrapingAgent(config=config)
        assert agent.config.max_retries == 10
        assert agent.config.min_content_length == 500
        assert agent.config.enable_selector_inference is False
        assert agent.config.respect_robots is False

    def test_init_with_kwargs_backward_compatibility(self):
        """Should correctly use legacy keyword arguments for configuration."""
        agent = ScrapingAgent(
            max_retries=3,
            min_content_length=50,
            enable_selector_inference=True,
            respect_robots=False,
        )
        assert agent.config.max_retries == 3
        assert agent.config.min_content_length == 50
        assert agent.config.enable_selector_inference is True
        assert agent.config.respect_robots is False

    def test_init_defaults(self):
        """Should use default values when no config or kwargs are provided."""
        agent = ScrapingAgent()
        assert agent.config.max_retries == 5
        assert agent.config.min_content_length == 100
        assert agent.config.enable_selector_inference is True
        assert agent.config.respect_robots is True

    def test_init_partial_kwargs(self):
        """Should use default values for missing keyword arguments."""
        agent = ScrapingAgent(max_retries=7)
        assert agent.config.max_retries == 7
        assert agent.config.min_content_length == 100  # Default
        assert agent.config.enable_selector_inference is True  # Default
