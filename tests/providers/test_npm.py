"""Tests for npm provider functions."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from src.mcp_server_pacman.providers.npm import search_npm, get_npm_info
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR

from tests.utils.test_utils import async_test

# Disable caching for tests
import src.mcp_server_pacman.utils.cache

src.mcp_server_pacman.utils.cache.ENABLE_CACHE = False


class TestNPMFunctions(unittest.TestCase):
    """Tests for npm search and info functions."""

    @patch("httpx.AsyncClient")
    @async_test
    async def test_search_npm_success(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "objects": [
                {
                    "package": {
                        "name": "express",
                        "version": "4.18.2",
                        "description": "Fast web framework",
                        "publisher": {"username": "dougwilson"},
                        "date": "2022-10-08",
                        "links": {"homepage": "http://expressjs.com/"},
                    }
                },
                {
                    "package": {
                        "name": "express-session",
                        "version": "1.17.3",
                        "description": "Session middleware",
                        "publisher": {"username": "dougwilson"},
                    }
                },
            ]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        results = await search_npm("express", 2)

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://registry.npmjs.org/-/v1/search",
            params={"text": "express", "size": 2},
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "express")
        self.assertEqual(results[1]["name"], "express-session")

    @patch("httpx.AsyncClient")
    @async_test
    async def test_search_npm_error_status(self, mock_client):
        # Setup mock for error status
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await search_npm("express", 2)

        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn("Failed to search npm", context.exception.error.message)

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_npm_info_success(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "express",
            "dist-tags": {"latest": "4.18.2"},
            "versions": {
                "4.18.2": {
                    "name": "express",
                    "version": "4.18.2",
                    "description": "Fast web framework",
                    "author": "TJ Holowaychuk",
                    "homepage": "http://expressjs.com/",
                    "license": "MIT",
                    "dependencies": {"accepts": "~1.3.8"},
                },
                "4.18.1": {},
            },
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        result = await get_npm_info("express")

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://registry.npmjs.org/express",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(result["name"], "express")
        self.assertEqual(result["version"], "4.18.2")
        self.assertEqual(result["description"], "Fast web framework")
        self.assertTrue("versions" in result)
        self.assertListEqual(result["versions"], ["4.18.2", "4.18.1"])

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_npm_info_with_version(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "express",
            "version": "4.17.1",
            "description": "Fast web framework",
            "author": "TJ Holowaychuk",
            "homepage": "http://expressjs.com/",
            "license": "MIT",
            "dependencies": {"accepts": "~1.3.7"},
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function with specific version
        result = await get_npm_info("express", "4.17.1")

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://registry.npmjs.org/express/4.17.1",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(result["version"], "4.17.1")
        self.assertTrue("dependencies" in result)

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_npm_info_error_status(self, mock_client):
        # Setup mock for error status
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await get_npm_info("nonexistent-package")

        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn(
            "Failed to get package info from npm", context.exception.error.message
        )


if __name__ == "__main__":
    unittest.main()
