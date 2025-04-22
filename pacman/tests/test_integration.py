"""
Integration tests for package index API calls.

These tests make real API calls to package registries.
Run these tests with:
    uv run pytest -xvs tests/test_integration.py

NOTE: These tests should NOT be run in CI/CD pipelines as they depend on
external services and may be rate-limited or fail due to network issues.
"""

import asyncio
import sys
import os

# Add the src directory to the path so we can import modules from there
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from src.mcp_server_pacman.server import (
    search_pypi,
    get_pypi_info,
    search_npm,
    get_npm_info,
    search_crates,
    get_crates_info,
)

# Make sure caching is enabled for integration tests
import src.mcp_server_pacman.server

src.mcp_server_pacman.server.ENABLE_CACHE = True


# Helper to run async tests
def async_test(coroutine):
    def wrapper(*args, **kwargs):
        asyncio.run(coroutine(*args, **kwargs))

    return wrapper


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


class TestNpmIntegration:
    """Integration tests for npm API functions."""

    @async_test
    async def test_search_npm_real(self):
        """Test searching npm for a popular package."""
        results = await search_npm("express", 3)
        assert len(results) > 0
        # Check that some expected fields are present
        for result in results:
            assert "name" in result
            assert "version" in result

    @async_test
    async def test_get_npm_info_real(self):
        """Test getting package info from npm for a known package."""
        result = await get_npm_info("express")
        assert result["name"] == "express"
        assert "version" in result
        assert "description" in result
        # These fields may not always be present
        assert "author" in result or "homepage" in result
        assert "versions" in result
        assert len(result["versions"]) > 0


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
