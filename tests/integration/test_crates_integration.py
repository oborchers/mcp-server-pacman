"""
Integration tests for crates.io API calls.

These tests make real API calls to package registries.
Run these tests with:
    uv run pytest -xvs tests/integration/test_crates_integration.py

NOTE: These tests should NOT be run in CI/CD pipelines as they depend on
external services and may be rate-limited or fail due to network issues.
"""

import sys
import os

# Add the src directory to the path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.mcp_server_pacman.providers.crates import search_crates, get_crates_info
from tests.utils.test_utils import async_test

# Make sure caching is enabled for integration tests
import src.mcp_server_pacman.utils.cache

src.mcp_server_pacman.utils.cache.ENABLE_CACHE = True


class TestCratesIntegration:
    """Integration tests for crates.io API functions."""

    @async_test
    async def test_search_crates_real(self):
        """Test searching crates.io for a popular package."""
        results = await search_crates("serde", 3)
        assert len(results) > 0
        # Check that some expected fields are present
        for result in results:
            assert "name" in result
            assert "version" in result

    @async_test
    async def test_get_crates_info_real(self):
        """Test getting package info from crates.io for a known package."""
        result = await get_crates_info("serde")
        assert result["name"] == "serde"
        assert "version" in result
        assert "description" in result or "homepage" in result
        assert "versions" in result
        assert len(result["versions"]) > 0
