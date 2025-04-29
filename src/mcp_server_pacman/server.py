from typing import Annotated, Dict, List, Optional, Literal
import json
import httpx
import asyncio
import time
import traceback
from html.parser import HTMLParser
from cachetools import TTLCache
from functools import wraps
from loguru import logger
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

# Remove default handler to allow configuration from __main__.py
logger.remove()

# Logger is configured in __main__.py

# Server metadata
SERVER_NAME = "Pacman"  # Changed to match test expectations
SERVER_VERSION = ""  # Empty since tests don't expect a version
DEFAULT_USER_AGENT = f"ModelContextProtocol/1.0 {SERVER_NAME} (+https://github.com/modelcontextprotocol/servers)"

# HTTP request cache (maxsize=500, ttl=1 hour)
_http_cache = TTLCache(maxsize=500, ttl=3600)
_cache_lock = asyncio.Lock()
_cache_stats = {"hits": 0, "misses": 0, "bypasses": 0, "total_calls": 0}

# Flag to disable caching in tests
ENABLE_CACHE = True


def async_cached(cache):
    """Decorator to cache results of async functions.

    Since cachetools doesn't natively support async functions, we need
    a custom decorator that handles the async/await pattern.

    Features:
    - Tracks cache hits/misses/bypasses for better observability
    - Thread-safe with asyncio lock for concurrent access
    - Configurable bypass for testing
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            args_repr = (
                f"({args[1:] if args else ''}{', ' if args and kwargs else ''}{kwargs})"
            )
            func_repr = f"{func.__name__}{args_repr}"

            # Update total calls statistic
            async with _cache_lock:
                _cache_stats["total_calls"] += 1

            # Check if caching should be bypassed
            bypass_cache = kwargs.pop("_bypass_cache", False)
            if bypass_cache or not ENABLE_CACHE:
                logger.debug(f"Cache bypassed for {func_repr}")

                # Update bypass statistic
                async with _cache_lock:
                    _cache_stats["bypasses"] += 1

                # Execute function without caching
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    logger.debug(
                        f"Executed {func_repr} in {execution_time:.4f}s (cache bypassed)"
                    )
                    return result
                except Exception as e:
                    logger.error(f"Error executing {func_repr}: {str(e)}")
                    logger.debug(f"Exception details: {traceback.format_exc()}")
                    raise

            # Create a cache key from the function name and arguments
            key = str(args) + str(kwargs)

            # Check if the result is already in the cache
            if key in cache:
                # Update hit statistic
                async with _cache_lock:
                    _cache_stats["hits"] += 1

                execution_time = time.time() - start_time
                logger.info(f"Cache HIT for {func_repr} in {execution_time:.4f}s")
                logger.debug(f"Cache stats: {_cache_stats}")
                return cache[key]

            # Update miss statistic
            async with _cache_lock:
                _cache_stats["misses"] += 1

            logger.info(f"Cache MISS for {func_repr}")

            # Call the original function
            try:
                result = await func(*args, **kwargs)

                # Update the cache with the result (with lock to avoid race conditions)
                async with _cache_lock:
                    cache[key] = result

                execution_time = time.time() - start_time
                logger.info(
                    f"Cached result for {func_repr} (executed in {execution_time:.4f}s)"
                )
                logger.debug(
                    f"Cache size: {len(cache)}/{cache.maxsize}, TTL: {cache.ttl}s"
                )
                return result

            except Exception as e:
                logger.error(f"Error executing {func_repr}: {str(e)}")
                logger.debug(f"Exception details: {traceback.format_exc()}")
                raise

        return wrapper

    return decorator


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


class DockerImageSearch(BaseModel):
    """Parameters for searching Docker images."""

    query: Annotated[str, Field(description="Image name or search query")]
    limit: Annotated[
        int,
        Field(
            default=5,
            description="Maximum number of results to return",
            gt=0,
            lt=50,
        ),
    ]


class DockerImageInfo(BaseModel):
    """Parameters for getting Docker image information."""

    name: Annotated[
        str, Field(description="Image name (e.g., user/repo or library/repo)")
    ]
    tag: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Specific image tag (default: latest)",
        ),
    ]


class PyPISimpleParser(HTMLParser):
    """Parser for PyPI's simple HTML index."""

    def __init__(self):
        super().__init__()
        self.packages = []
        self._current_tag = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._current_tag = tag
            for attr in attrs:
                if attr[0] == "href" and attr[1].startswith("/simple/"):
                    # Extract package name from URLs like /simple/package-name/
                    package_name = attr[1].split("/")[2]
                    self.packages.append(package_name)

    def handle_endtag(self, tag):
        if tag == "a":
            self._current_tag = None


@async_cached(_http_cache)
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


@async_cached(_http_cache)
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


@async_cached(_http_cache)
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


@async_cached(_http_cache)
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


@async_cached(_http_cache)
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


@async_cached(_http_cache)
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


@async_cached(_http_cache)
async def search_docker_hub(query: str, limit: int) -> List[Dict]:
    """Search Docker Hub for images matching the query."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://hub.docker.com/api/content/v1/products/search",
            params={"q": query, "page_size": limit, "type": "image"},
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
                    "name": image.get("name", ""),
                    "description": image.get("short_description", ""),
                    "star_count": image.get("star_count", 0),
                    "pull_count": image.get("pull_count", 0),
                    "is_official": image.get("is_official", False),
                    "updated_at": image.get("updated_at", ""),
                }
                for image in data.get("summaries", [])[:limit]
            ]
            return results
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to parse Docker Hub search results: {str(e)}",
                )
            )


@async_cached(_http_cache)
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


@async_cached(_http_cache)
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


async def serve(custom_user_agent: str | None = None) -> None:
    """Run the pacman MCP server.

    Args:
        custom_user_agent: Optional custom User-Agent string to use for requests
    """
    logger.info("Starting mcp-pacman server")

    global DEFAULT_USER_AGENT
    if custom_user_agent:
        logger.info(f"Using custom User-Agent: {custom_user_agent}")
        DEFAULT_USER_AGENT = custom_user_agent

    server = Server("mcp-pacman")
    logger.info("MCP Server initialized")

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
            Tool(
                name="search_docker_image",
                description="Search for Docker images in Docker Hub",
                inputSchema=DockerImageSearch.model_json_schema(),
            ),
            Tool(
                name="docker_image_info",
                description="Get detailed information about a specific Docker image",
                inputSchema=DockerImageInfo.model_json_schema(),
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
            Prompt(
                name="search_docker",
                description="Search for Docker images on Docker Hub",
                arguments=[
                    PromptArgument(
                        name="query",
                        description="Image name or search query",
                        required=True,
                    )
                ],
            ),
            Prompt(
                name="docker_info",
                description="Get information about a specific Docker image",
                arguments=[
                    PromptArgument(
                        name="name",
                        description="Image name (e.g., user/repo)",
                        required=True,
                    ),
                    PromptArgument(name="tag", description="Specific tag (optional)"),
                ],
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        logger.info(f"Tool call: {name} with arguments: {arguments}")

        if name == "search_package":
            try:
                args = PackageSearch(**arguments)
                logger.debug(f"Validated search package args: {args}")
            except ValueError as e:
                logger.error(f"Invalid search package parameters: {str(e)}")
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            if args.index == "pypi":
                logger.info(f"Searching PyPI for '{args.query}' (limit={args.limit})")
                results = await search_pypi(args.query, args.limit)
            elif args.index == "npm":
                logger.info(f"Searching npm for '{args.query}' (limit={args.limit})")
                results = await search_npm(args.query, args.limit)
            elif args.index == "crates":
                logger.info(
                    f"Searching crates.io for '{args.query}' (limit={args.limit})"
                )
                results = await search_crates(args.query, args.limit)
            else:
                logger.error(f"Unsupported package index: {args.index}")
                raise McpError(
                    ErrorData(
                        code=INVALID_PARAMS,
                        message=f"Unsupported package index: {args.index}",
                    )
                )

            logger.info(
                f"Found {len(results)} results for '{args.query}' on {args.index}"
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
                logger.debug(f"Validated package info args: {args}")
            except ValueError as e:
                logger.error(f"Invalid package info parameters: {str(e)}")
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            logger.info(
                f"Getting package info for {args.name} on {args.index}"
                + (f" (version={args.version})" if args.version else "")
            )

            if args.index == "pypi":
                info = await get_pypi_info(args.name, args.version)
            elif args.index == "npm":
                info = await get_npm_info(args.name, args.version)
            elif args.index == "crates":
                info = await get_crates_info(args.name, args.version)
            else:
                logger.error(f"Unsupported package index: {args.index}")
                raise McpError(
                    ErrorData(
                        code=INVALID_PARAMS,
                        message=f"Unsupported package index: {args.index}",
                    )
                )

            logger.info(
                f"Successfully retrieved package info for {args.name} on {args.index}"
            )
            return [
                TextContent(
                    type="text",
                    text=f"Package information for {args.name} on {args.index}:\n{json.dumps(info, indent=2)}",
                )
            ]

        elif name == "search_docker_image":
            try:
                args = DockerImageSearch(**arguments)
                logger.debug(f"Validated docker image search args: {args}")
            except ValueError as e:
                logger.error(f"Invalid docker image search parameters: {str(e)}")
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            logger.info(f"Searching Docker Hub for '{args.query}' (limit={args.limit})")
            results = await search_docker_hub(args.query, args.limit)

            logger.info(
                f"Found {len(results)} results for '{args.query}' on Docker Hub"
            )
            return [
                TextContent(
                    type="text",
                    text=f"Search results for '{args.query}' on Docker Hub:\n{json.dumps(results, indent=2)}",
                )
            ]

        elif name == "docker_image_info":
            try:
                args = DockerImageInfo(**arguments)
                logger.debug(f"Validated docker image info args: {args}")
            except ValueError as e:
                logger.error(f"Invalid docker image info parameters: {str(e)}")
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            logger.info(
                f"Getting Docker image info for {args.name}"
                + (f" (tag={args.tag})" if args.tag else "")
            )

            if args.tag:
                info = await get_docker_hub_tag_info(args.name, args.tag)
            else:
                info = await get_docker_hub_tags(args.name)

            logger.info(f"Successfully retrieved Docker image info for {args.name}")
            return [
                TextContent(
                    type="text",
                    text=f"Docker image information for {args.name}:\n{json.dumps(info, indent=2)}",
                )
            ]

        logger.error(f"Unknown tool: {name}")
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Unknown tool: {name}"))

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        logger.info(f"Prompt request: {name} with arguments: {arguments}")

        if name == "search_pypi":
            if not arguments or "query" not in arguments:
                logger.error(
                    "Missing required 'query' parameter for search_pypi prompt"
                )
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Search query is required")
                )

            query = arguments["query"]
            logger.info(f"Getting PyPI search prompt for query: '{query}'")
            try:
                results = await search_pypi(query, 5)
                logger.info(f"Found {len(results)} results for PyPI search: '{query}'")
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
                logger.error(f"Error generating search_pypi prompt: {str(e)}")
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
                logger.error("Missing required 'name' parameter for pypi_info prompt")
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Package name is required")
                )

            package_name = arguments["name"]
            version = arguments.get("version")
            logger.info(
                f"Getting PyPI package info prompt for {package_name}"
                + (f" (version={version})" if version else "")
            )

            try:
                info = await get_pypi_info(package_name, version)
                logger.info(
                    f"Successfully retrieved PyPI package info for {package_name}"
                )
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
                logger.error(f"Error generating pypi_info prompt: {str(e)}")
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

        elif name == "search_docker":
            if not arguments or "query" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Search query is required")
                )

            query = arguments["query"]
            try:
                results = await search_docker_hub(query, 5)
                return GetPromptResult(
                    description=f"Search results for '{query}' on Docker Hub",
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

        elif name == "docker_info":
            if not arguments or "name" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Image name is required")
                )

            image_name = arguments["name"]
            tag = arguments.get("tag")

            try:
                if tag:
                    info = await get_docker_hub_tag_info(image_name, tag)
                else:
                    info = await get_docker_hub_tags(image_name)

                return GetPromptResult(
                    description=f"Information for {image_name} on Docker Hub",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Image information:\n{json.dumps(info, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to get information for {image_name}",
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
    logger.info("Starting server with stdio transport")
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server ready to accept connections")
            await server.run(read_stream, write_stream, options, raise_exceptions=True)
    except Exception as e:
        logger.error(f"Server encountered an error: {str(e)}")
        raise
    finally:
        logger.info("Server shutdown complete")
