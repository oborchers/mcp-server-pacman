"""Tests for Docker Hub provider functions."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from src.mcp_server_pacman.providers.dockerhub import (
    search_docker_hub,
    get_docker_hub_tags,
    get_docker_hub_tag_info,
)
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR

from tests.utils.test_utils import async_test

# Disable caching for tests
import src.mcp_server_pacman.utils.cache

src.mcp_server_pacman.utils.cache.ENABLE_CACHE = False


class TestDockerHubFunctions(unittest.TestCase):
    """Tests for Docker Hub search and info functions."""

    @patch("httpx.AsyncClient")
    @async_test
    async def test_search_docker_hub_success(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "repo_name": "nginx",
                    "description": "Official NGINX image",
                    "star_count": 15000,
                    "pull_count": 10000000,
                    "is_official": True,
                    "last_updated": "2022-10-01T00:00:00Z",
                },
                {
                    "repo_name": "nginxinc/nginx-unprivileged",
                    "description": "Unprivileged NGINX image",
                    "star_count": 100,
                    "pull_count": 10000,
                    "is_official": False,
                    "last_updated": "2022-09-15T00:00:00Z",
                },
            ]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        results = await search_docker_hub("nginx", 2)

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://hub.docker.com/v2/search/repositories",
            params={"query": "nginx", "page_size": 2},
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "nginx")
        self.assertEqual(results[0]["is_official"], True)
        self.assertEqual(results[1]["name"], "nginxinc/nginx-unprivileged")

    @patch("httpx.AsyncClient")
    @async_test
    async def test_search_docker_hub_error_status(self, mock_client):
        # Setup mock for error status
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await search_docker_hub("nginx", 2)

        # Verify API call was made with the updated URL
        mock_client_instance.get.assert_called_once_with(
            "https://hub.docker.com/v2/search/repositories",
            params={"query": "nginx", "page_size": 2},
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn("Failed to search Docker Hub", context.exception.error.message)

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_docker_hub_tags_success(self, mock_client):
        # Setup mocks for both API calls (tags and repository info)
        tags_response = MagicMock()
        tags_response.status_code = 200
        tags_response.json.return_value = {
            "count": 2,
            "results": [
                {
                    "name": "latest",
                    "last_updated": "2022-10-01T00:00:00Z",
                    "digest": "sha256:123",
                    "images": [
                        {
                            "architecture": "amd64",
                            "os": "linux",
                            "size": 100000000,
                        }
                    ],
                },
                {
                    "name": "1.25.0",
                    "last_updated": "2022-09-15T00:00:00Z",
                    "digest": "sha256:456",
                    "images": [
                        {
                            "architecture": "amd64",
                            "os": "linux",
                            "size": 90000000,
                        }
                    ],
                },
            ],
        }

        repo_response = MagicMock()
        repo_response.status_code = 200
        repo_response.json.return_value = {
            "description": "Official NGINX image",
            "star_count": 15000,
            "pull_count": 10000000,
            "is_official": True,
            "last_updated": "2022-10-01T00:00:00Z",
        }

        mock_client_instance = AsyncMock()
        # Configure the mock to return different responses for different calls
        mock_client_instance.get.side_effect = [tags_response, repo_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        result = await get_docker_hub_tags("nginx")

        # Verify calls were made (should be two calls)
        self.assertEqual(mock_client_instance.get.call_count, 2)
        # First call should be to get tags
        mock_client_instance.get.assert_any_call(
            "https://hub.docker.com/v2/repositories/library/nginx/tags",
            params={"page_size": 25, "ordering": "last_updated"},
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        # Second call should be to get repo info
        mock_client_instance.get.assert_any_call(
            "https://hub.docker.com/v2/repositories/library/nginx",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )

        # Verify results
        self.assertEqual(result["name"], "library/nginx")
        self.assertEqual(len(result["tags"]), 2)
        self.assertEqual(result["tag_count"], 2)
        self.assertEqual(result["tags"][0]["name"], "latest")
        self.assertEqual(result["tags"][1]["name"], "1.25.0")
        self.assertEqual(result["repository"]["is_official"], True)

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_docker_hub_tag_info_success(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "latest",
            "last_updated": "2022-10-01T00:00:00Z",
            "full_size": 100000000,
            "digest": "sha256:123",
            "images": [
                {
                    "architecture": "amd64",
                    "os": "linux",
                    "size": 100000000,
                }
            ],
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        result = await get_docker_hub_tag_info("nginx", "latest")

        # Verify call was made
        mock_client_instance.get.assert_called_once_with(
            "https://hub.docker.com/v2/repositories/library/nginx/tags/latest",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )

        # Verify results
        self.assertEqual(result["name"], "library/nginx")
        self.assertEqual(result["tag"], "latest")
        self.assertEqual(result["digest"], "sha256:123")
        self.assertEqual(result["full_size"], 100000000)
        self.assertEqual(len(result["images"]), 1)
        self.assertEqual(result["images"][0]["architecture"], "amd64")

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_docker_hub_tag_info_error_status(self, mock_client):
        # Setup mock for error status
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await get_docker_hub_tag_info("nonexistent-image", "latest")

        # Verify API call was made
        mock_client_instance.get.assert_called_once()
        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn("Failed to get tag info", context.exception.error.message)


if __name__ == "__main__":
    unittest.main()
