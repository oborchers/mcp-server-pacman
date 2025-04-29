"""Tests for the Terraform Registry provider."""

import unittest
from unittest.mock import patch, MagicMock
from mcp.shared.exceptions import McpError

from src.mcp_server_pacman.providers.terraform import (
    search_terraform_modules,
    get_terraform_module_info,
    get_latest_terraform_module_version,
)


class TestTerraformFunctions(unittest.IsolatedAsyncioTestCase):
    """Test case for Terraform Registry provider functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable caching for tests
        self.cache_patcher = patch(
            "src.mcp_server_pacman.providers.terraform.http_cache", {}
        )
        self.cache_patcher.start()

        # Sample search response
        self.search_response = {
            "meta": {"limit": 5, "current_offset": 0},
            "modules": [
                {
                    "id": "hashicorp/consul/aws",
                    "namespace": "hashicorp",
                    "name": "consul",
                    "provider": "aws",
                    "version": "0.11.0",
                    "description": "Terraform module for deploying Consul on AWS",
                    "source": "https://github.com/hashicorp/terraform-aws-consul",
                    "published_at": "2023-06-15T12:30:00Z",
                    "downloads": 10000,
                    "verified": True,
                },
                {
                    "id": "hashicorp/nomad/aws",
                    "namespace": "hashicorp",
                    "name": "nomad",
                    "provider": "aws",
                    "version": "0.8.0",
                    "description": "Terraform module for deploying Nomad on AWS",
                    "source": "https://github.com/hashicorp/terraform-aws-nomad",
                    "published_at": "2023-05-10T15:45:00Z",
                    "downloads": 8000,
                    "verified": True,
                },
            ],
        }

        # Sample module info response
        self.module_info_response = {
            "id": "hashicorp/consul/aws",
            "namespace": "hashicorp",
            "name": "consul",
            "provider": "aws",
            "version": "0.11.0",
            "description": "Terraform module for deploying Consul on AWS",
            "source": "https://github.com/hashicorp/terraform-aws-consul",
            "published_at": "2023-06-15T12:30:00Z",
            "downloads": 10000,
            "owner": "hashicorp",
            "verified": True,
            "root": {
                "path": "",
                "readme": "# Consul AWS Module\n\nThis module deploys Consul on AWS.",
                "empty": False,
                "inputs": [
                    {
                        "name": "ami_id",
                        "type": "string",
                        "description": "The ID of the AMI to run in the cluster",
                        "default": "",
                        "required": True,
                    }
                ],
                "outputs": [
                    {
                        "name": "asg_name",
                        "description": "Name of the autoscaling group",
                    }
                ],
                "dependencies": [],
                "resources": [],
            },
        }

        # Sample versions response
        self.versions_response = {
            "modules": [
                {
                    "version": "0.11.0",
                    "published_at": "2023-06-15T12:30:00Z",
                    "source": "https://github.com/hashicorp/terraform-aws-consul",
                },
                {
                    "version": "0.10.0",
                    "published_at": "2023-04-20T10:15:00Z",
                    "source": "https://github.com/hashicorp/terraform-aws-consul",
                },
                {
                    "version": "0.9.0",
                    "published_at": "2023-02-05T14:10:00Z",
                    "source": "https://github.com/hashicorp/terraform-aws-consul",
                },
            ]
        }

    def tearDown(self):
        """Tear down test fixtures."""
        self.cache_patcher.stop()

    @patch("httpx.AsyncClient.get")
    async def test_search_terraform_modules_success(self, mock_get):
        """Test successful search for Terraform modules."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.search_response
        mock_get.return_value = mock_response

        # Call the function
        results = await search_terraform_modules("consul", 5)

        # Check the results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "hashicorp/consul/aws")
        self.assertEqual(
            results[0]["description"], "Terraform module for deploying Consul on AWS"
        )
        self.assertEqual(results[0]["downloads"], 10000)
        self.assertEqual(results[0]["version"], "0.11.0")

        # Check that the correct URL was called
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["q"], "consul")
        self.assertEqual(kwargs["params"]["limit"], 5)

    @patch("httpx.AsyncClient.get")
    async def test_search_terraform_modules_error(self, mock_get):
        """Test error handling for Terraform module search."""
        # Set up the mock to return an error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Call the function and check for exception
        with self.assertRaises(McpError) as context:
            await search_terraform_modules("consul", 5)

        self.assertIn("Failed to search Terraform Registry", str(context.exception))

    @patch("httpx.AsyncClient.get")
    async def test_get_terraform_module_info_success(self, mock_get):
        """Test successful retrieval of Terraform module info."""
        # Set up the mocks for both API calls
        module_response = MagicMock()
        module_response.status_code = 200
        module_response.json.return_value = self.module_info_response

        versions_response = MagicMock()
        versions_response.status_code = 200
        versions_response.json.return_value = self.versions_response

        # Our code makes two HTTP requests, but the implementation may use different ordering
        # Let the code access either URL and return the appropriate mock response
        def side_effect(url, **kwargs):
            if "/versions" in url:
                return versions_response
            return module_response

        mock_get.side_effect = side_effect

        # Call the function
        result = await get_terraform_module_info("hashicorp/consul/aws")

        # Check the structure of the result
        self.assertEqual(result["name"], "hashicorp/consul/aws")
        self.assertEqual(result["namespace"], "hashicorp")
        self.assertEqual(result["module"], "consul")
        self.assertEqual(result["provider"], "aws")

        # Check that required fields exist
        self.assertIn("version", result)
        self.assertIn("source", result)

        # Versions field might be included depending on implementation details
        if "versions" in result:
            self.assertIsInstance(result["versions"], list)

    @patch("httpx.AsyncClient.get")
    async def test_get_terraform_module_invalid_name(self, mock_get):
        """Test handling of invalid module name format."""
        with self.assertRaises(McpError) as context:
            await get_terraform_module_info("invalid-format")

        self.assertIn("Invalid Terraform module name format", str(context.exception))
        mock_get.assert_not_called()

    @patch("httpx.AsyncClient.get")
    async def test_get_latest_terraform_module_version_success(self, mock_get):
        """Test successful retrieval of the latest Terraform module version."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.versions_response
        mock_get.return_value = mock_response

        # Call the function
        result = await get_latest_terraform_module_version("hashicorp/consul/aws")

        # Check the results
        self.assertEqual(result["name"], "hashicorp/consul/aws")
        self.assertEqual(result["namespace"], "hashicorp")
        self.assertEqual(result["module"], "consul")
        self.assertEqual(result["provider"], "aws")
        self.assertEqual(result["version"], "0.11.0")
        self.assertEqual(result["published_at"], "2023-06-15T12:30:00Z")

    @patch("httpx.AsyncClient.get")
    async def test_get_latest_terraform_module_version_no_versions(self, mock_get):
        """Test handling of a module with no versions."""
        # Set up the mock to return empty versions
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"modules": []}
        mock_get.return_value = mock_response

        # Call the function and check for exception
        with self.assertRaises(McpError) as context:
            await get_latest_terraform_module_version("hashicorp/consul/aws")

        self.assertIn("No versions found for module", str(context.exception))


if __name__ == "__main__":
    unittest.main()
