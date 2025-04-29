"""
Integration tests for Docker Hub API calls.

These tests make real API calls to Docker Hub.
Run these tests with:
    uv run pytest -xvs tests/test_docker_integration.py

NOTE: These tests should NOT be run in CI/CD pipelines as they depend on
external services and may be rate-limited or fail due to network issues.
"""

import asyncio
import sys
import os
import httpx

# Add the src directory to the path so we can import modules from there
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from src.mcp_server_pacman.server import (
    search_docker_hub,
    get_docker_hub_tags,
    get_docker_hub_tag_info,
)

# Make sure caching is enabled for integration tests
import src.mcp_server_pacman.server

src.mcp_server_pacman.server.ENABLE_CACHE = True


# Helper to run async tests
def async_test(coroutine):
    def wrapper(*args, **kwargs):
        asyncio.run(coroutine(*args, **kwargs))

    return wrapper


class TestDockerHubIntegration:
    """Integration tests for Docker Hub API functions."""

    @async_test
    async def test_search_docker_hub_real(self):
        """Test searching Docker Hub via our function for a popular image."""
        results = await search_docker_hub("nginx", 3)
        assert len(results) > 0

        # Check that our standardized fields are present
        for result in results:
            assert "name" in result  # We map repo_name to name in our function
            assert "pull_count" in result
            assert "is_official" in result

    @async_test
    async def test_get_docker_hub_tags_real(self):
        """Test getting tags from Docker Hub for a known image."""
        result = await get_docker_hub_tags("nginx")
        assert result["name"] == "library/nginx"
        assert "tags" in result
        assert len(result["tags"]) > 0
        assert "tag_count" in result
        assert "repository" in result

        # Check tag structure
        for tag in result["tags"]:
            assert "name" in tag
            assert "digest" in tag
            assert "images" in tag

            # Check image structure within tag
            for image in tag["images"]:
                assert "architecture" in image
                assert "os" in image
                assert "size" in image

    @async_test
    async def test_get_docker_hub_tag_info_real(self):
        """Test getting tag info from Docker Hub for a known image and tag."""
        result = await get_docker_hub_tag_info("nginx", "latest")
        assert result["name"] == "library/nginx"
        assert result["tag"] == "latest"
        assert "digest" in result
        assert "full_size" in result
        assert "images" in result

        # Check image structure
        for image in result["images"]:
            assert "architecture" in image
            assert "os" in image
            assert "size" in image

    @async_test
    async def test_official_image_no_namespace(self):
        """Test that Docker Hub API works with official images specified without namespace."""
        result = await get_docker_hub_tag_info("ubuntu", "latest")
        assert result["name"] == "library/ubuntu"
        assert result["tag"] == "latest"
        assert "digest" in result
        assert "images" in result

    @async_test
    async def test_user_namespaced_image(self):
        """Test that Docker Hub API works with user-namespaced images."""
        # bitnami is a well-known publisher with stable images
        result = await get_docker_hub_tags("bitnami/nginx")
        assert result["name"] == "bitnami/nginx"
        assert "tags" in result
        assert len(result["tags"]) > 0
