"""Crates.io package index provider."""

from typing import Dict, List, Optional
import httpx
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..utils.cache import async_cached, http_cache
from ..utils.constants import DEFAULT_USER_AGENT


@async_cached(http_cache)
async def search_crates(query: str, limit: int) -> List[Dict]:
    """Search crates.io for packages matching the query."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://crates.io/api/v1/crates",
            params={"q": query, "per_page": limit},
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to search crates.io - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            results = [
                {
                    "name": crate["name"],
                    "version": crate["max_version"],
                    "description": crate.get("description", ""),
                    "downloads": crate.get("downloads", 0),
                    "created_at": crate.get("created_at", ""),
                    "updated_at": crate.get("updated_at", ""),
                }
                for crate in data.get("crates", [])[:limit]
            ]
            return results
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse crates.io search results: {str(e)}",
                )
            )


@async_cached(http_cache)
async def get_crates_info(name: str, version: Optional[str] = None) -> Dict:
    """Get information about a package from crates.io."""
    async with httpx.AsyncClient() as client:
        # First get the crate info
        url = f"https://crates.io/api/v1/crates/{name}"
        response = await client.get(
            url,
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get package info from crates.io - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            crate = data["crate"]

            # If a specific version was requested, get that version's details
            version_data = {}
            if version:
                version_url = f"https://crates.io/api/v1/crates/{name}/{version}"
                version_response = await client.get(
                    version_url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": DEFAULT_USER_AGENT,
                    },
                    follow_redirects=True,
                )

                if version_response.status_code == 200:
                    version_data = version_response.json().get("version", {})

            # If no specific version, use the latest
            if not version_data and data.get("versions"):
                version = data["versions"][0]["num"]  # Latest version
                version_data = data["versions"][0]

            result = {
                "name": crate["name"],
                "version": version or crate.get("max_version", ""),
                "description": crate.get("description", ""),
                "homepage": crate.get("homepage", ""),
                "documentation": crate.get("documentation", ""),
                "repository": crate.get("repository", ""),
                "downloads": crate.get("downloads", 0),
                "recent_downloads": crate.get("recent_downloads", 0),
                "categories": crate.get("categories", []),
                "keywords": crate.get("keywords", []),
                "versions": [v["num"] for v in data.get("versions", [])],
                "yanked": version_data.get("yanked", False) if version_data else False,
                "license": version_data.get("license", "") if version_data else "",
            }
            return result
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse crates.io package info: {str(e)}",
                )
            )
