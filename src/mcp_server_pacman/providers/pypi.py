"""PyPI package index provider."""

from typing import Dict, List, Optional
import httpx
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..utils.cache import async_cached, http_cache
from ..utils.constants import DEFAULT_USER_AGENT
from ..utils.parsers import PyPISimpleParser


@async_cached(http_cache)
async def search_pypi(query: str, limit: int) -> List[Dict]:
    """Search PyPI for packages matching the query using the simple index."""
    async with httpx.AsyncClient() as client:
        # First get the full package list from the simple index
        response = await client.get(
            "https://pypi.org/simple/",
            headers={"Accept": "text/html", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to search PyPI - status code {response.status_code}",
                )
            )

        try:
            # Parse the HTML to extract package names
            parser = PyPISimpleParser()
            parser.feed(response.text)

            # Filter packages that match the query (case insensitive)
            query_lower = query.lower()
            matching_packages = [
                pkg for pkg in parser.packages if query_lower in pkg.lower()
            ]

            # Sort by relevance (exact matches first, then startswith, then contains)
            matching_packages.sort(
                key=lambda pkg: (
                    0
                    if pkg.lower() == query_lower
                    else 1
                    if pkg.lower().startswith(query_lower)
                    else 2
                )
            )

            # Limit the results
            matching_packages = matching_packages[:limit]

            # For each match, get basic details (we'll fetch more details on demand)
            results = []
            for pkg_name in matching_packages:
                # Create a result entry with the information we have
                results.append(
                    {
                        "name": pkg_name,
                        "version": "latest",  # We don't have version info from the simple index
                        "description": f"Python package: {pkg_name}",
                    }
                )

            return results
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse PyPI search results: {str(e)}",
                )
            )


@async_cached(http_cache)
async def get_pypi_info(name: str, version: Optional[str] = None) -> Dict:
    """Get information about a package from PyPI."""
    async with httpx.AsyncClient() as client:
        url = f"https://pypi.org/pypi/{name}/json"
        if version:
            url = f"https://pypi.org/pypi/{name}/{version}/json"

        response = await client.get(
            url,
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get package info from PyPI - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            result = {
                "name": data["info"]["name"],
                "version": data["info"]["version"],
                "description": data["info"]["summary"],
                "author": data["info"]["author"],
                "homepage": data["info"]["home_page"],
                "license": data["info"]["license"],
                "releases": list(data["releases"].keys()),
            }
            return result
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse PyPI package info: {str(e)}",
                )
            )
