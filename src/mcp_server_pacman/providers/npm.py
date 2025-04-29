"""npm package index provider."""

from typing import Dict, List, Optional
import httpx
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..utils.cache import async_cached, http_cache
from ..utils.constants import DEFAULT_USER_AGENT


@async_cached(http_cache)
async def search_npm(query: str, limit: int) -> List[Dict]:
    """Search npm for packages matching the query."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://registry.npmjs.org/-/v1/search",
            params={"text": query, "size": limit},
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to search npm - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            results = [
                {
                    "name": package["package"]["name"],
                    "version": package["package"]["version"],
                    "description": package["package"].get("description", ""),
                    "publisher": package["package"]
                    .get("publisher", {})
                    .get("username", ""),
                    "date": package["package"].get("date", ""),
                    "links": package["package"].get("links", {}),
                }
                for package in data.get("objects", [])[:limit]
            ]
            return results
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse npm search results: {str(e)}",
                )
            )


@async_cached(http_cache)
async def get_npm_info(name: str, version: Optional[str] = None) -> Dict:
    """Get information about a package from npm."""
    async with httpx.AsyncClient() as client:
        url = f"https://registry.npmjs.org/{name}"
        if version:
            url = f"https://registry.npmjs.org/{name}/{version}"

        response = await client.get(
            url,
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get package info from npm - status code {response.status_code}",
                )
            )

        try:
            data = response.json()

            # For specific version request
            if version:
                return {
                    "name": data.get("name", name),
                    "version": data.get("version", version),
                    "description": data.get("description", ""),
                    "author": data.get("author", ""),
                    "homepage": data.get("homepage", ""),
                    "license": data.get("license", ""),
                    "dependencies": data.get("dependencies", {}),
                }

            # For latest/all versions
            latest_version = data.get("dist-tags", {}).get("latest", "")
            latest_info = data.get("versions", {}).get(latest_version, {})

            return {
                "name": data.get("name", name),
                "version": latest_version,
                "description": latest_info.get("description", ""),
                "author": latest_info.get("author", ""),
                "homepage": latest_info.get("homepage", ""),
                "license": latest_info.get("license", ""),
                "dependencies": latest_info.get("dependencies", {}),
                "versions": list(data.get("versions", {}).keys()),
            }
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse npm package info: {str(e)}",
                )
            )
