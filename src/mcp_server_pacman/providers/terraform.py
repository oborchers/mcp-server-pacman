"""Terraform Registry provider."""

from typing import Dict, List
import httpx
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..utils.cache import async_cached, http_cache
from ..utils.constants import DEFAULT_USER_AGENT


@async_cached(http_cache)
async def search_terraform_modules(query: str, limit: int) -> List[Dict]:
    """Search Terraform Registry for modules matching the query."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://registry.terraform.io/v1/modules/search",
            params={"q": query, "limit": limit},
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to search Terraform Registry - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            results = [
                {
                    "name": f"{module.get('namespace', '')}/{module.get('name', '')}/{module.get('provider', '')}",
                    "description": module.get("description", ""),
                    "downloads": module.get("downloads", 0),
                    "version": module.get("version", ""),
                    "source": module.get("source", ""),
                    "published_at": module.get("published_at", ""),
                }
                for module in data.get("modules", [])[:limit]
            ]
            return results
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse Terraform Registry search results: {str(e)}",
                )
            )


@async_cached(http_cache)
async def get_terraform_module_info(name: str) -> Dict:
    """Get information about a Terraform module.

    The name parameter should be in the format: namespace/name/provider
    """
    # Split the module name into namespace, name, and provider
    parts = name.split("/")
    if len(parts) != 3:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message="Invalid Terraform module name format. Expected: namespace/name/provider",
            )
        )

    namespace, module_name, provider = parts

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://registry.terraform.io/v1/modules/{namespace}/{module_name}/{provider}",
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get module info from Terraform Registry - status code {response.status_code}",
                )
            )

        try:
            data = response.json()

            # Get versions
            versions_response = await client.get(
                f"https://registry.terraform.io/v1/modules/{namespace}/{module_name}/{provider}/versions",
                headers={
                    "Accept": "application/json",
                    "User-Agent": DEFAULT_USER_AGENT,
                },
                follow_redirects=True,
            )

            versions = []
            if versions_response.status_code == 200:
                versions_data = versions_response.json()
                versions = [
                    v.get("version", "") for v in versions_data.get("modules", [])
                ]

            result = {
                "id": data.get("id", ""),
                "name": f"{namespace}/{module_name}/{provider}",
                "namespace": namespace,
                "provider": provider,
                "module": module_name,
                "version": data.get("version", ""),
                "description": data.get("description", ""),
                "source": data.get("source", ""),
                "published_at": data.get("published_at", ""),
                "downloads": data.get("downloads", 0),
                "versions": versions,
                "owner": data.get("owner", ""),
                "root": data.get("root", {}),
            }
            return result
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse Terraform Registry module info: {str(e)}",
                )
            )


@async_cached(http_cache)
async def get_latest_terraform_module_version(name: str) -> Dict:
    """Get the latest version of a Terraform module.

    The name parameter should be in the format: namespace/name/provider
    """
    # Split the module name into namespace, name, and provider
    parts = name.split("/")
    if len(parts) != 3:
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message="Invalid Terraform module name format. Expected: namespace/name/provider",
            )
        )

    namespace, module_name, provider = parts

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://registry.terraform.io/v1/modules/{namespace}/{module_name}/{provider}/versions",
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

        if response.status_code != 200:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to get module versions from Terraform Registry - status code {response.status_code}",
                )
            )

        try:
            data = response.json()
            modules = data.get("modules", [])

            if not modules:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message=f"No versions found for module {name}",
                    )
                )

            # The latest version is typically the first one in the list
            latest = modules[0]

            result = {
                "name": f"{namespace}/{module_name}/{provider}",
                "namespace": namespace,
                "provider": provider,
                "module": module_name,
                "version": latest.get("version", ""),
                "published_at": latest.get("published_at", ""),
                "source": latest.get("source", ""),
            }
            return result
        except McpError:
            raise
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse Terraform Registry module versions: {str(e)}",
                )
            )
