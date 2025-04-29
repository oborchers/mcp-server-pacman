"""Tests for crates.io provider functions."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from src.mcp_server_pacman.providers.crates import search_crates, get_crates_info
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR

from tests.utils.test_utils import async_test

# Disable caching for tests
import src.mcp_server_pacman.utils.cache

src.mcp_server_pacman.utils.cache.ENABLE_CACHE = False


class TestCratesFunctions(unittest.TestCase):
    """Tests for crates.io search and info functions."""

    @patch("httpx.AsyncClient")
    @async_test
    async def test_search_crates_success(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "crates": [
                {
                    "name": "serde",
                    "max_version": "1.0.171",
                    "description": "Serialization framework",
                    "downloads": 500000,
                    "created_at": "2015-12-10T08:40:51.513183+00:00",
                    "updated_at": "2023-06-12T19:08:09.978746+00:00",
                },
                {
                    "name": "serde_json",
                    "max_version": "1.0.103",
                    "description": "JSON support for serde",
                    "downloads": 400000,
                },
            ]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        results = await search_crates("serde", 2)

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://crates.io/api/v1/crates",
            params={"q": "serde", "per_page": 2},
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "serde")
        self.assertEqual(results[0]["version"], "1.0.171")
        self.assertEqual(results[1]["name"], "serde_json")

    @patch("httpx.AsyncClient")
    @async_test
    async def test_search_crates_error_status(self, mock_client):
        # Setup mock for error status
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await search_crates("serde", 2)

        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn("Failed to search crates.io", context.exception.error.message)

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_crates_info_success(self, mock_client):
        # Setup mocks for both API calls
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "crate": {
                "name": "serde",
                "max_version": "1.0.171",
                "description": "Serialization framework",
                "homepage": "https://serde.rs",
                "documentation": "https://docs.rs/serde",
                "repository": "https://github.com/serde-rs/serde",
                "downloads": 500000,
                "recent_downloads": 10000,
                "categories": ["encoding"],
                "keywords": ["serialization"],
            },
            "versions": [{"num": "1.0.171"}, {"num": "1.0.170"}],
        }

        # Create a mock AsyncClient instance
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response1
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        result = await get_crates_info("serde")

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://crates.io/api/v1/crates/serde",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(result["name"], "serde")
        self.assertEqual(result["description"], "Serialization framework")
        self.assertEqual(result["homepage"], "https://serde.rs")
        self.assertListEqual(result["versions"], ["1.0.171", "1.0.170"])

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_crates_info_with_version(self, mock_client):
        # Setup mocks
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "crate": {
                "name": "serde",
                "max_version": "1.0.171",
                "description": "Serialization framework",
                "homepage": "https://serde.rs",
            },
            "versions": [{"num": "1.0.171"}, {"num": "1.0.170"}],
        }

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "version": {
                "num": "1.0.170",
                "yanked": False,
                "license": "MIT OR Apache-2.0",
            }
        }

        # Create a mock AsyncClient instance that returns different responses
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [mock_response1, mock_response2]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function with specific version
        result = await get_crates_info("serde", "1.0.170")

        # Verify calls
        self.assertEqual(mock_client_instance.get.call_count, 2)
        mock_client_instance.get.assert_any_call(
            "https://crates.io/api/v1/crates/serde",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        mock_client_instance.get.assert_any_call(
            "https://crates.io/api/v1/crates/serde/1.0.170",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )

        # Verify results
        self.assertEqual(result["name"], "serde")
        self.assertEqual(result["version"], "1.0.170")
        self.assertEqual(result["license"], "MIT OR Apache-2.0")
        self.assertFalse(result["yanked"])

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_crates_info_error_status(self, mock_client):
        # Setup mock for error status
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await get_crates_info("nonexistent-package")

        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn(
            "Failed to get package info from crates.io", context.exception.error.message
        )


if __name__ == "__main__":
    unittest.main()
