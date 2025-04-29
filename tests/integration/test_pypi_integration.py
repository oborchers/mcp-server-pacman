"""
Integration tests for PyPI API calls.

These tests make real API calls to package registries.
Run these tests with:
    uv run pytest -xvs tests/integration/test_pypi_integration.py

NOTE: These tests should NOT be run in CI/CD pipelines as they depend on
external services and may be rate-limited or fail due to network issues.
"""

import sys
import os

# Add the src directory to the path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.mcp_server_pacman.providers.pypi import search_pypi, get_pypi_info
from tests.utils.test_utils import async_test

# Make sure caching is enabled for integration tests
import src.mcp_server_pacman.utils.cache

src.mcp_server_pacman.utils.cache.ENABLE_CACHE = True


class TestPyPIIntegration:
    """Integration tests for PyPI API functions."""

    @async_test
    async def test_search_pypi_real(self):
        """Test searching PyPI for a popular package."""
        results = await search_pypi("requests", 3)
        assert len(results) > 0
        # Check that some expected fields are present
        for result in results:
            assert "name" in result
            assert "version" in result
            assert "description" in result

    @async_test
    async def test_get_pypi_info_real(self):
        """Test getting package info from PyPI for a known package."""
        result = await get_pypi_info("requests")
        assert result["name"] == "requests"
        assert "version" in result
        assert "description" in result
        assert "author" in result
        assert "homepage" in result
        assert "license" in result
        assert len(result["releases"]) > 0
