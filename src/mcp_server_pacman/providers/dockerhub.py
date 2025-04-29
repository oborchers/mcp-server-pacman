"""Docker Hub image provider."""

from typing import Dict, List
import httpx
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..utils.cache import async_cached, http_cache
from ..utils.constants import DEFAULT_USER_AGENT


@async_cached(http_cache)
async def search_docker_hub(query: str, limit: int) -> List[Dict]:
    """Search Docker Hub for images matching the query."""
    async with httpx.AsyncClient() as client:
        # Use the v2 API for more reliable results
        response = await client.get(
            "https://hub.docker.com/v2/search/repositories",
            params={"query": query, "page_size": limit},
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to search Docker Hub - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            results = [
                {
                    "name": image.get(
                        "repo_name", ""
                    ),  # Using repo_name as the name field
                    "description": image.get("description", "")
                    or image.get("short_description", ""),
                    "star_count": image.get("star_count", 0),
                    "pull_count": image.get("pull_count", 0),
                    "is_official": image.get("is_official", False),
                    "updated_at": image.get("last_updated", "")
                    or image.get("updated_at", ""),
                }
                for image in data.get("results", [])[:limit]
            ]
            return results
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse Docker Hub search results: {str(e)}",
                )
            )


@async_cached(http_cache)
async def get_docker_hub_tags(name: str) -> Dict:
    """Get information about tags for a specific Docker image."""
    # Split the image name into namespace and repository
    if "/" in name:
        namespace, repository = name.split("/", 1)
    else:
        namespace, repository = "library", name

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://hub.docker.com/v2/repositories/{namespace}/{repository}/tags",
            params={"page_size": 25, "ordering": "last_updated"},
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get image tags from Docker Hub - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            tags = [
                {
                    "name": tag.get("name", ""),
                    "last_updated": tag.get("last_updated", ""),
                    "digest": tag.get("digest", ""),
                    "images": [
                        {
                            "architecture": img.get("architecture", ""),
                            "os": img.get("os", ""),
                            "size": img.get("size", 0),
                        }
                        for img in tag.get("images", [])
                    ],
                }
                for tag in data.get("results", [])
            ]

            # Get repo information
            repo_response = await client.get(
                f"https://hub.docker.com/v2/repositories/{namespace}/{repository}",
                headers={
                    "Accept": "application/json",
                    "User-Agent": DEFAULT_USER_AGENT,
                },
                follow_redirects=True,
            )
            repo_info = {}
            if repo_response.status_code == 200:
                repo_data = repo_response.json()
                repo_info = {
                    "description": repo_data.get("description", ""),
                    "star_count": repo_data.get("star_count", 0),
                    "pull_count": repo_data.get("pull_count", 0),
                    "is_official": repo_data.get("is_official", False),
                    "last_updated": repo_data.get("last_updated", ""),
                }

            return {
                "name": f"{namespace}/{repository}",
                "tags": tags,
                "tag_count": data.get("count", 0),
                "repository": repo_info,
            }
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse Docker Hub tags response: {str(e)}",
                )
            )


@async_cached(http_cache)
async def get_docker_hub_tag_info(name: str, tag: str = "latest") -> Dict:
    """Get information about a specific tag of a Docker image."""
    # Split the image name into namespace and repository
    if "/" in name:
        namespace, repository = name.split("/", 1)
    else:
        namespace, repository = "library", name

    async with httpx.AsyncClient() as client:
        tag_url = f"https://hub.docker.com/v2/repositories/{namespace}/{repository}/tags/{tag}"
        response = await client.get(
            tag_url,
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get tag info for {name}:{tag} - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            result = {
                "name": f"{namespace}/{repository}",
                "tag": tag,
                "last_updated": data.get("last_updated", ""),
                "full_size": data.get("full_size", 0),
                "digest": data.get("digest", ""),
                "images": [
                    {
                        "architecture": img.get("architecture", ""),
                        "os": img.get("os", ""),
                        "size": img.get("size", 0),
                    }
                    for img in data.get("images", [])
                ],
            }
            return result
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse Docker Hub tag info: {str(e)}",
                )
            )
