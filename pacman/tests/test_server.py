import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from src.mcp_server_pacman.server import (
    search_pypi, get_pypi_info,
    search_npm, get_npm_info,
    search_crates, get_crates_info,
    PackageSearch, PackageInfo
)
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR

class TestPackageModels(unittest.TestCase):
    """Tests for the PackageSearch and PackageInfo models."""
    
    def test_package_search_valid(self):
        # Test valid package search
        search = PackageSearch(index="pypi", query="requests", limit=10)
        self.assertEqual(search.index, "pypi")
        self.assertEqual(search.query, "requests")
        self.assertEqual(search.limit, 10)
        
    def test_package_search_invalid_index(self):
        # Test invalid index
        with self.assertRaises(ValueError):
            PackageSearch(index="invalid", query="requests", limit=10)
    
    def test_package_search_invalid_limit(self):
        # Test invalid limit (too high)
        with self.assertRaises(ValueError):
            PackageSearch(index="pypi", query="requests", limit=100)
        
        # Test invalid limit (too low)
        with self.assertRaises(ValueError):
            PackageSearch(index="pypi", query="requests", limit=0)
    
    def test_package_info_valid(self):
        # Test valid package info
        info = PackageInfo(index="pypi", name="requests")
        self.assertEqual(info.index, "pypi")
        self.assertEqual(info.name, "requests")
        self.assertIsNone(info.version)
        
        # Test with version
        info = PackageInfo(index="pypi", name="requests", version="2.28.1")
        self.assertEqual(info.index, "pypi")
        self.assertEqual(info.name, "requests")
        self.assertEqual(info.version, "2.28.1")
    
    def test_package_info_invalid_index(self):
        # Test invalid index
        with self.assertRaises(ValueError):
            PackageInfo(index="invalid", name="requests")


class TestPyPIFunctions(unittest.TestCase):
    """Tests for PyPI search and info functions."""
    
    @patch('httpx.AsyncClient')
    async def test_search_pypi_success(self, mock_client):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Execute function
        results = await search_pypi("requests", 3)
        
        # Verify calls and results
        mock_client_instance.get.assert_called_once()
        self.assertEqual(len(results), 3)
        for i, result in enumerate(results):
            self.assertEqual(result["name"], f"example-{i}")
    
    @patch('httpx.AsyncClient')
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
        
        self.assertEqual(context.exception.error.code, INTERNAL_ERROR)
        self.assertIn("Failed to search PyPI", context.exception.error.message)
    
    @patch('httpx.AsyncClient')
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
                "license": "Apache 2.0"
            },
            "releases": {"2.28.1": {}, "2.28.0": {}}
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Execute function
        result = await get_pypi_info("requests")
        
        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://pypi.org/pypi/requests/json",
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        self.assertEqual(result["name"], "requests")
        self.assertEqual(result["version"], "2.28.1")
        self.assertEqual(result["description"], "HTTP library")
        self.assertEqual(result["author"], "Kenneth Reitz")
        self.assertEqual(result["releases"], ["2.28.1", "2.28.0"])
    
    @patch('httpx.AsyncClient')
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
                "license": "Apache 2.0"
            },
            "releases": {"2.27.0": {}}
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Execute function with specific version
        result = await get_pypi_info("requests", "2.27.0")
        
        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://pypi.org/pypi/requests/2.27.0/json",
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        self.assertEqual(result["version"], "2.27.0")
    
    @patch('httpx.AsyncClient')
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
        self.assertIn("Failed to get package info from PyPI", context.exception.error.message)
    
    @patch('httpx.AsyncClient')
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
        self.assertIn("Failed to parse PyPI package info", context.exception.error.message)


class TestNPMFunctions(unittest.TestCase):
    """Tests for npm search and info functions."""
    
    @patch('httpx.AsyncClient')
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
                        "links": {"homepage": "http://expressjs.com/"}
                    }
                },
                {
                    "package": {
                        "name": "express-session",
                        "version": "1.17.3",
                        "description": "Session middleware",
                        "publisher": {"username": "dougwilson"}
                    }
                }
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
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "express")
        self.assertEqual(results[1]["name"], "express-session")
    
    @patch('httpx.AsyncClient')
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
    
    @patch('httpx.AsyncClient')
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
                    "dependencies": {"accepts": "~1.3.8"}
                },
                "4.18.1": {}
            }
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Execute function
        result = await get_npm_info("express")
        
        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://registry.npmjs.org/express",
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        self.assertEqual(result["name"], "express")
        self.assertEqual(result["version"], "4.18.2")
        self.assertEqual(result["description"], "Fast web framework")
        self.assertTrue("versions" in result)
        self.assertListEqual(result["versions"], ["4.18.2", "4.18.1"])
    
    @patch('httpx.AsyncClient')
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
            "dependencies": {"accepts": "~1.3.7"}
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Execute function with specific version
        result = await get_npm_info("express", "4.17.1")
        
        # Verify calls and results
        mock_client_instance.get.assert_called_once_with(
            "https://registry.npmjs.org/express/4.17.1",
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        self.assertEqual(result["version"], "4.17.1")
        self.assertTrue("dependencies" in result)
    
    @patch('httpx.AsyncClient')
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
        self.assertIn("Failed to get package info from npm", context.exception.error.message)


class TestCratesFunctions(unittest.TestCase):
    """Tests for crates.io search and info functions."""
    
    @patch('httpx.AsyncClient')
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
                    "updated_at": "2023-06-12T19:08:09.978746+00:00"
                },
                {
                    "name": "serde_json",
                    "max_version": "1.0.103",
                    "description": "JSON support for serde",
                    "downloads": 400000
                }
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
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "serde")
        self.assertEqual(results[0]["version"], "1.0.171")
        self.assertEqual(results[1]["name"], "serde_json")
    
    @patch('httpx.AsyncClient')
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
    
    @patch('httpx.AsyncClient')
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
                "keywords": ["serialization"]
            },
            "versions": [
                {"num": "1.0.171"},
                {"num": "1.0.170"}
            ]
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
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        self.assertEqual(result["name"], "serde")
        self.assertEqual(result["description"], "Serialization framework")
        self.assertEqual(result["homepage"], "https://serde.rs")
        self.assertListEqual(result["versions"], ["1.0.171", "1.0.170"])
    
    @patch('httpx.AsyncClient')
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
            "versions": [
                {"num": "1.0.171"},
                {"num": "1.0.170"}
            ]
        }
        
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "version": {
                "num": "1.0.170",
                "yanked": False,
                "license": "MIT OR Apache-2.0"
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
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        mock_client_instance.get.assert_any_call(
            "https://crates.io/api/v1/crates/serde/1.0.170",
            headers={"Accept": "application/json", "User-Agent": "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"},
            follow_redirects=True,
        )
        
        # Verify results
        self.assertEqual(result["name"], "serde")
        self.assertEqual(result["version"], "1.0.170")
        self.assertEqual(result["license"], "MIT OR Apache-2.0")
        self.assertFalse(result["yanked"])
    
    @patch('httpx.AsyncClient')
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
        self.assertIn("Failed to get package info from crates.io", context.exception.error.message)


from src.mcp_server_pacman.server import Server

class TestToolCalls(unittest.TestCase):
    """Tests for server tool and prompt handlers."""
    
    @patch('src.mcp_server_pacman.server.search_pypi')
    @patch('src.mcp_server_pacman.server.search_npm')
    @patch('src.mcp_server_pacman.server.search_crates')
    async def test_call_tool_search_package(self, mock_search_crates, mock_search_npm, mock_search_pypi):
        # Setup mocks
        mock_search_pypi.return_value = [{"name": "requests"}]
        mock_search_npm.return_value = [{"name": "express"}]
        mock_search_crates.return_value = [{"name": "serde"}]
        
        # Create server instance
        server = Server("test-pacman")
        
        # Add call_tool method to server
        from src.mcp_server_pacman.server import serve
        await serve()
        
        # Get the call_tool implementation
        call_tool_impl = server._callbacks.get("call_tool")
        
        # Test PyPI search
        result = await call_tool_impl("search_package", {"index": "pypi", "query": "requests", "limit": 5})
        mock_search_pypi.assert_called_once_with("requests", 5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("pypi", result[0].text)
        
        # Test npm search
        result = await call_tool_impl("search_package", {"index": "npm", "query": "express", "limit": 5})
        mock_search_npm.assert_called_once_with("express", 5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("npm", result[0].text)
        
        # Test crates search
        result = await call_tool_impl("search_package", {"index": "crates", "query": "serde", "limit": 5})
        mock_search_crates.assert_called_once_with("serde", 5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("crates", result[0].text)
    
    @patch('src.mcp_server_pacman.server.get_pypi_info')
    @patch('src.mcp_server_pacman.server.get_npm_info')
    @patch('src.mcp_server_pacman.server.get_crates_info')
    async def test_call_tool_package_info(self, mock_get_crates_info, mock_get_npm_info, mock_get_pypi_info):
        # Setup mocks
        mock_get_pypi_info.return_value = {"name": "requests", "version": "2.28.1"}
        mock_get_npm_info.return_value = {"name": "express", "version": "4.18.2"}
        mock_get_crates_info.return_value = {"name": "serde", "version": "1.0.171"}
        
        # Create server instance
        server = Server("test-pacman")
        
        # Add call_tool method to server
        from src.mcp_server_pacman.server import serve
        await serve()
        
        # Get the call_tool implementation
        call_tool_impl = server._callbacks.get("call_tool")
        
        # Test PyPI info
        result = await call_tool_impl("package_info", {"index": "pypi", "name": "requests"})
        mock_get_pypi_info.assert_called_once_with("requests", None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("pypi", result[0].text)
        
        # Test npm info
        result = await call_tool_impl("package_info", {"index": "npm", "name": "express", "version": "4.18.2"})
        mock_get_npm_info.assert_called_once_with("express", "4.18.2")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("npm", result[0].text)
        
        # Test crates info
        result = await call_tool_impl("package_info", {"index": "crates", "name": "serde"})
        mock_get_crates_info.assert_called_once_with("serde", None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("crates", result[0].text)
    
    async def test_call_tool_invalid_tool(self):
        # Create server instance
        server = Server("test-pacman")
        
        # Add call_tool method to server
        from src.mcp_server_pacman.server import serve
        await serve()
        
        # Get the call_tool implementation
        call_tool_impl = server._callbacks.get("call_tool")
        
        # Test invalid tool name
        with self.assertRaises(McpError) as context:
            await call_tool_impl("invalid_tool", {})
        
        self.assertEqual(context.exception.error.code, INVALID_PARAMS)
        self.assertIn("Unknown tool", context.exception.error.message)
    
    async def test_call_tool_invalid_params(self):
        # Create server instance
        server = Server("test-pacman")
        
        # Add call_tool method to server
        from src.mcp_server_pacman.server import serve
        await serve()
        
        # Get the call_tool implementation
        call_tool_impl = server._callbacks.get("call_tool")
        
        # Test invalid parameters
        with self.assertRaises(McpError) as context:
            await call_tool_impl("search_package", {"index": "invalid", "query": "test"})
        
        self.assertEqual(context.exception.error.code, INVALID_PARAMS)
    
    @patch('src.mcp_server_pacman.server.search_pypi')
    async def test_get_prompt_search_pypi(self, mock_search_pypi):
        # Setup mock
        mock_search_pypi.return_value = [{"name": "requests", "version": "2.28.1"}]
        
        # Create server instance
        server = Server("test-pacman")
        
        # Add get_prompt method to server
        from src.mcp_server_pacman.server import serve
        await serve()
        
        # Get the get_prompt implementation
        get_prompt_impl = server._callbacks.get("get_prompt")
        
        # Test successful search
        result = await get_prompt_impl("search_pypi", {"query": "requests"})
        
        self.assertEqual(result.description, "Search results for 'requests' on PyPI")
        self.assertEqual(len(result.messages), 1)
        self.assertEqual(result.messages[0].role, "user")
        self.assertEqual(result.messages[0].content.type, "text")
        self.assertIn("Results for 'requests'", result.messages[0].content.text)
        
        # Test missing query
        with self.assertRaises(McpError) as context:
            await get_prompt_impl("search_pypi", {})
        
        self.assertEqual(context.exception.error.code, INVALID_PARAMS)
        self.assertIn("Search query is required", context.exception.error.message)
    
    @patch('src.mcp_server_pacman.server.get_pypi_info')
    async def test_get_prompt_pypi_info(self, mock_get_pypi_info):
        # Setup mock
        mock_get_pypi_info.return_value = {"name": "requests", "version": "2.28.1"}
        
        # Create server instance
        server = Server("test-pacman")
        
        # Add get_prompt method to server
        from src.mcp_server_pacman.server import serve
        await serve()
        
        # Get the get_prompt implementation
        get_prompt_impl = server._callbacks.get("get_prompt")
        
        # Test successful info retrieval
        result = await get_prompt_impl("pypi_info", {"name": "requests"})
        
        self.assertEqual(result.description, "Information for requests on PyPI")
        self.assertEqual(len(result.messages), 1)
        self.assertEqual(result.messages[0].role, "user")
        self.assertEqual(result.messages[0].content.type, "text")
        self.assertIn("Package information", result.messages[0].content.text)
        
        # Test with version
        result = await get_prompt_impl("pypi_info", {"name": "requests", "version": "2.28.1"})
        mock_get_pypi_info.assert_called_with("requests", "2.28.1")
        
        # Test missing name
        with self.assertRaises(McpError) as context:
            await get_prompt_impl("pypi_info", {})
        
        self.assertEqual(context.exception.error.code, INVALID_PARAMS)
        self.assertIn("Package name is required", context.exception.error.message)
    
    async def test_get_prompt_invalid_prompt(self):
        # Create server instance
        server = Server("test-pacman")
        
        # Add get_prompt method to server
        from src.mcp_server_pacman.server import serve
        await serve()
        
        # Get the get_prompt implementation
        get_prompt_impl = server._callbacks.get("get_prompt")
        
        # Test invalid prompt name
        with self.assertRaises(McpError) as context:
            await get_prompt_impl("invalid_prompt", {})
        
        self.assertEqual(context.exception.error.code, INVALID_PARAMS)
        self.assertIn("Unknown prompt", context.exception.error.message)


def run_async_test(coro):
    return asyncio.run(coro)

if __name__ == "__main__":
    unittest.main()