"""Tests for PyPI provider functions."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from src.mcp_server_pacman.providers.pypi import search_pypi, get_pypi_info
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR

from tests.utils.test_utils import async_test

# Disable caching for tests
import src.mcp_server_pacman.utils.cache

src.mcp_server_pacman.utils.cache.ENABLE_CACHE = False


class TestPyPIFunctions(unittest.TestCase):
    """Tests for PyPI search and info functions."""

    @patch("httpx.AsyncClient")
    @async_test
    async def test_search_pypi_success(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Provide sample HTML that would be returned from PyPI simple index
        mock_response.text = """
        <html>
          <body>
            <a href="/simple/requests/">requests</a>
            <a href="/simple/requestsexceptions/">requestsexceptions</a>
            <a href="/simple/requests-cache/">requests-cache</a>
            <a href="/simple/requests-aws4auth/">requests-aws4auth</a>
            <a href="/simple/requests-toolbelt/">requests-toolbelt</a>
            <a href="/simple/another-package/">another-package</a>
          </body>
        </html>
        """

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        results = await search_pypi("requests", 3)

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://pypi.org/simple/",
            headers={
                "Accept": "text/html",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        # Should find 5 packages with "requests" in the name, but limit to 3
        self.assertEqual(len(results), 3)
        # The first one should be 'requests' (exact match)
        self.assertEqual(results[0]["name"], "requests")

    @patch("httpx.AsyncClient")
    @async_test
    async def test_search_pypi_error_status(self, mock_client):
        # Setup mock for error status
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await search_pypi("requests", 3)

        # Verify API call was made
        mock_client_instance.get.assert_called_once_with(
            "https://pypi.org/simple/",
            headers={
                "Accept": "text/html",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )

        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn("Failed to search PyPI", context.exception.error.message)

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_pypi_info_success(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "name": "requests",
                "version": "2.28.1",
                "summary": "HTTP library",
                "author": "Kenneth Reitz",
                "home_page": "https://requests.readthedocs.io",
                "license": "Apache 2.0",
            },
            "releases": {"2.28.1": {}, "2.28.0": {}},
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function
        result = await get_pypi_info("requests")

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://pypi.org/pypi/requests/json",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(result["name"], "requests")
        self.assertEqual(result["version"], "2.28.1")
        self.assertEqual(result["description"], "HTTP library")
        self.assertEqual(result["author"], "Kenneth Reitz")
        self.assertEqual(result["releases"], ["2.28.1", "2.28.0"])

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_pypi_info_with_version(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "name": "requests",
                "version": "2.27.0",
                "summary": "HTTP library",
                "author": "Kenneth Reitz",
                "home_page": "https://requests.readthedocs.io",
                "license": "Apache 2.0",
            },
            "releases": {"2.27.0": {}},
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute function with specific version
        result = await get_pypi_info("requests", "2.27.0")

        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://pypi.org/pypi/requests/2.27.0/json",
            headers={
                "Accept": "application/json",
                "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)",
            },
            follow_redirects=True,
        )
        self.assertEqual(result["version"], "2.27.0")

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_pypi_info_error_status(self, mock_client):
        # Setup mock for error status
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await get_pypi_info("nonexistent-package")

        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn(
            "Failed to get package info from PyPI", context.exception.error.message
        )

    @patch("httpx.AsyncClient")
    @async_test
    async def test_get_pypi_info_parse_error(self, mock_client):
        # Setup mock that raises error during json parsing
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = Exception("Invalid JSON")

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        # Execute and check for exception
        with self.assertRaises(McpError) as context:
            await get_pypi_info("requests")

        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn(
            "Failed to parse PyPI package info", context.exception.error.message
        )


if __name__ == "__main__":
    unittest.main()
