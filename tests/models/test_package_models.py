"""Tests for package model classes."""

import unittest

from src.mcp_server_pacman.models.package_models import (
    PackageSearch,
    PackageInfo,
    DockerImageSearch,
    DockerImageInfo,
)


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


class TestDockerModels(unittest.TestCase):
    """Tests for the DockerImageSearch and DockerImageInfo models."""

    def test_docker_image_search_valid(self):
        # Test valid docker image search
        search = DockerImageSearch(query="nginx", limit=10)
        self.assertEqual(search.query, "nginx")
        self.assertEqual(search.limit, 10)

    def test_docker_image_search_invalid_limit(self):
        # Test invalid limit (too high)
        with self.assertRaises(ValueError):
            DockerImageSearch(query="nginx", limit=100)

        # Test invalid limit (too low)
        with self.assertRaises(ValueError):
            DockerImageSearch(query="nginx", limit=0)

    def test_docker_image_info_valid(self):
        # Test valid docker image info
        info = DockerImageInfo(name="nginx")
        self.assertEqual(info.name, "nginx")
        self.assertIsNone(info.tag)

        # Test with tag
        info = DockerImageInfo(name="nginx", tag="1.25.0")
        self.assertEqual(info.name, "nginx")
        self.assertEqual(info.tag, "1.25.0")


if __name__ == "__main__":
    unittest.main()
