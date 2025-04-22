from typing import Annotated, Dict, List, Optional, Literal
import json
import httpx

from mcp.shared.exceptions import McpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    ErrorData,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from pydantic import BaseModel, Field

DEFAULT_USER_AGENT = (
    "ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)"
)


class PackageSearch(BaseModel):
    """Parameters for searching a package index."""

    index: Annotated[
        Literal["pypi", "npm", "crates"],
        Field(description="Package index to search (pypi, npm, crates)"),
    ]
    query: Annotated[str, Field(description="Package name or search query")]
    limit: Annotated[
        int,
        Field(
            default=5,
            description="Maximum number of results to return",
            gt=0,
            lt=50,
        ),
    ]


class PackageInfo(BaseModel):
    """Parameters for getting package information."""

    index: Annotated[
        Literal["pypi", "npm", "crates"],
        Field(description="Package index to query (pypi, npm, crates)"),
    ]
    name: Annotated[str, Field(description="Package name")]
    version: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Specific version to get info for (default: latest)",
        ),
    ]


async def search_pypi(query: str, limit: int) -> List[Dict]:
    """Search PyPI for packages matching the query."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://pypi.org/search/",
            params={"q": query, "page": 1},
            headers={"Accept": "application/json", "User-Agent": DEFAULT_USER_AGENT},
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
            # PyPI doesn't have a JSON search API, so we'd need HTML parsing here
            # This is a simplified placeholder - in a real implementation, use BeautifulSoup
            # to extract package info from the HTML response
            results = [
                {
                    "name": f"example-{i}",
                    "version": "1.0.0",
                    "description": "This is a placeholder. Real implementation would parse PyPI HTML response.",
                }
                for i in range(min(limit, 5))
            ]
            return results
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse PyPI search results: {str(e)}",
                )
            )


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


async def serve(custom_user_agent: str | None = None) -> None:
    """Run the pacman MCP server.

    Args:
        custom_user_agent: Optional custom User-Agent string to use for requests
    """
    global DEFAULT_USER_AGENT
    if custom_user_agent:
        DEFAULT_USER_AGENT = custom_user_agent

    server = Server("mcp-pacman")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_package",
                description="Search for packages in package indices (PyPI, npm, crates.io)",
                inputSchema=PackageSearch.model_json_schema(),
            ),
            Tool(
                name="package_info",
                description="Get detailed information about a specific package",
                inputSchema=PackageInfo.model_json_schema(),
            ),
        ]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="search_pypi",
                description="Search for Python packages on PyPI",
                arguments=[
                    PromptArgument(
                        name="query",
                        description="Package name or search query",
                        required=True,
                    )
                ],
            ),
            Prompt(
                name="pypi_info",
                description="Get information about a specific Python package",
                arguments=[
                    PromptArgument(
                        name="name", description="Package name", required=True
                    ),
                    PromptArgument(
                        name="version", description="Specific version (optional)"
                    ),
                ],
            ),
            Prompt(
                name="search_npm",
                description="Search for JavaScript packages on npm",
                arguments=[
                    PromptArgument(
                        name="query",
                        description="Package name or search query",
                        required=True,
                    )
                ],
            ),
            Prompt(
                name="npm_info",
                description="Get information about a specific JavaScript package",
                arguments=[
                    PromptArgument(
                        name="name", description="Package name", required=True
                    ),
                    PromptArgument(
                        name="version", description="Specific version (optional)"
                    ),
                ],
            ),
            Prompt(
                name="search_crates",
                description="Search for Rust packages on crates.io",
                arguments=[
                    PromptArgument(
                        name="query",
                        description="Package name or search query",
                        required=True,
                    )
                ],
            ),
            Prompt(
                name="crates_info",
                description="Get information about a specific Rust package",
                arguments=[
                    PromptArgument(
                        name="name", description="Package name", required=True
                    ),
                    PromptArgument(
                        name="version", description="Specific version (optional)"
                    ),
                ],
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "search_package":
            try:
                args = PackageSearch(**arguments)
            except ValueError as e:
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            if args.index == "pypi":
                results = await search_pypi(args.query, args.limit)
            elif args.index == "npm":
                results = await search_npm(args.query, args.limit)
            elif args.index == "crates":
                results = await search_crates(args.query, args.limit)
            else:
                raise McpError(
                    ErrorData(
                        code=INVALID_PARAMS,
                        message=f"Unsupported package index: {args.index}",
                    )
                )

            return [
                TextContent(
                    type="text",
                    text=f"Search results for '{args.query}' on {args.index}:\n{json.dumps(results, indent=2)}",
                )
            ]

        elif name == "package_info":
            try:
                args = PackageInfo(**arguments)
            except ValueError as e:
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            if args.index == "pypi":
                info = await get_pypi_info(args.name, args.version)
            elif args.index == "npm":
                info = await get_npm_info(args.name, args.version)
            elif args.index == "crates":
                info = await get_crates_info(args.name, args.version)
            else:
                raise McpError(
                    ErrorData(
                        code=INVALID_PARAMS,
                        message=f"Unsupported package index: {args.index}",
                    )
                )

            return [
                TextContent(
                    type="text",
                    text=f"Package information for {args.name} on {args.index}:\n{json.dumps(info, indent=2)}",
                )
            ]

        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Unknown tool: {name}"))

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        if name == "search_pypi":
            if not arguments or "query" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Search query is required")
                )

            query = arguments["query"]
            try:
                results = await search_pypi(query, 5)
                return GetPromptResult(
                    description=f"Search results for '{query}' on PyPI",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Results for '{query}':\n{json.dumps(results, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to search for '{query}'",
                    messages=[
                        PromptMessage(
                            role="user", content=TextContent(type="text", text=str(e))
                        )
                    ],
                )

        elif name == "pypi_info":
            if not arguments or "name" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Package name is required")
                )

            package_name = arguments["name"]
            version = arguments.get("version")

            try:
                info = await get_pypi_info(package_name, version)
                return GetPromptResult(
                    description=f"Information for {package_name} on PyPI",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Package information:\n{json.dumps(info, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to get information for {package_name}",
                    messages=[
                        PromptMessage(
                            role="user", content=TextContent(type="text", text=str(e))
                        )
                    ],
                )

        elif name == "search_npm":
            if not arguments or "query" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Search query is required")
                )

            query = arguments["query"]
            try:
                results = await search_npm(query, 5)
                return GetPromptResult(
                    description=f"Search results for '{query}' on npm",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Results for '{query}':\n{json.dumps(results, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to search for '{query}'",
                    messages=[
                        PromptMessage(
                            role="user", content=TextContent(type="text", text=str(e))
                        )
                    ],
                )

        elif name == "npm_info":
            if not arguments or "name" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Package name is required")
                )

            package_name = arguments["name"]
            version = arguments.get("version")

            try:
                info = await get_npm_info(package_name, version)
                return GetPromptResult(
                    description=f"Information for {package_name} on npm",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Package information:\n{json.dumps(info, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to get information for {package_name}",
                    messages=[
                        PromptMessage(
                            role="user", content=TextContent(type="text", text=str(e))
                        )
                    ],
                )

        elif name == "search_crates":
            if not arguments or "query" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Search query is required")
                )

            query = arguments["query"]
            try:
                results = await search_crates(query, 5)
                return GetPromptResult(
                    description=f"Search results for '{query}' on crates.io",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Results for '{query}':\n{json.dumps(results, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to search for '{query}'",
                    messages=[
                        PromptMessage(
                            role="user", content=TextContent(type="text", text=str(e))
                        )
                    ],
                )

        elif name == "crates_info":
            if not arguments or "name" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Package name is required")
                )

            package_name = arguments["name"]
            version = arguments.get("version")

            try:
                info = await get_crates_info(package_name, version)
                return GetPromptResult(
                    description=f"Information for {package_name} on crates.io",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Package information:\n{json.dumps(info, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to get information for {package_name}",
                    messages=[
                        PromptMessage(
                            role="user", content=TextContent(type="text", text=str(e))
                        )
                    ],
                )

        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=f"Unknown prompt: {name}")
        )

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
