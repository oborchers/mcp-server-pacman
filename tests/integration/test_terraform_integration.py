"""Integration tests for the Terraform Registry provider."""

import unittest

from src.mcp_server_pacman.providers.terraform import (
    search_terraform_modules,
    get_terraform_module_info,
    get_latest_terraform_module_version,
)
from src.mcp_server_pacman.utils.cache import ENABLE_CACHE


class TestTerraformIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for Terraform Registry provider."""

    def setUp(self):
        """Set up test fixtures."""
        # Use a different popular module for testing
        self.test_module = "terraform-aws-modules/vpc/aws"
        self.test_search_term = "hashicorp"

        # For integration tests, we disable caching to ensure fresh results
        global ENABLE_CACHE
        self.original_cache_setting = ENABLE_CACHE
        ENABLE_CACHE = False

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore original cache setting
        global ENABLE_CACHE
        ENABLE_CACHE = self.original_cache_setting

    async def test_search_terraform_modules(self):
        """Test searching for Terraform modules in the registry."""
        try:
            results = await search_terraform_modules(self.test_search_term, 5)
            self.assertIsInstance(results, list)
            self.assertLessEqual(len(results), 5)

            # Verify the structure of returned items
            if results:
                item = results[0]
                self.assertIn("name", item)
                self.assertIn("description", item)
                self.assertIn("version", item)
                self.assertIn("downloads", item)

                # The name should include namespace/name/provider format
                name_parts = item["name"].split("/")
                self.assertEqual(len(name_parts), 3)
        except Exception as e:
            self.fail(f"Search operation failed: {str(e)}")

    async def test_get_terraform_module_info(self):
        """Test getting information about a specific Terraform module."""
        try:
            info = await get_terraform_module_info(self.test_module)
            self.assertIsInstance(info, dict)

            # Print the info for debugging
            print(f"Module info: {info}")

            # Verify the structure of the returned info
            self.assertIn("name", info)
            self.assertIn("namespace", info)
            self.assertIn("module", info)
            self.assertIn("provider", info)
            self.assertIn("version", info)

            # Some fields might be empty in real-world API responses
            if "versions" in info:
                self.assertIsInstance(info["versions"], list)

            # Verify that the name matches the input module
            self.assertEqual(info["name"], self.test_module)
        except Exception as e:
            self.fail(f"Module info operation failed: {str(e)}")

    async def test_get_latest_terraform_module_version(self):
        """Test getting the latest version of a Terraform module."""
        try:
            version_info = await get_latest_terraform_module_version(self.test_module)
            self.assertIsInstance(version_info, dict)

            # Verify the structure of the returned version info
            self.assertIn("name", version_info)
            self.assertIn("namespace", version_info)
            self.assertIn("module", version_info)
            self.assertIn("provider", version_info)
            self.assertIn("version", version_info)
            self.assertIn("published_at", version_info)

            # Verify that the name matches the input module
            self.assertEqual(version_info["name"], self.test_module)

            # Print the whole version_info for debugging
            print(f"Version info: {version_info}")

            # Version should be a string
            version = version_info["version"]
            self.assertIsInstance(version, str)
        except Exception as e:
            self.fail(f"Latest version operation failed: {str(e)}")


if __name__ == "__main__":
    unittest.main()
