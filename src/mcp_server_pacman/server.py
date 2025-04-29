"""MCP Server implementation for Pacman package index tools."""

import json
from typing import Optional
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
)

# Import models
from .models import (
    PackageSearch,
    PackageInfo,
    DockerImageSearch,
    DockerImageInfo,
    TerraformModuleLatestVersion,
)

# Import providers
from .providers import (
    search_pypi,
    get_pypi_info,
    search_npm,
    get_npm_info,
    search_crates,
    get_crates_info,
    search_docker_hub,
    get_docker_hub_tags,
    get_docker_hub_tag_info,
    search_terraform_modules,
    get_terraform_module_info,
    get_latest_terraform_module_version,
)

# Import constants

# Remove default handler to allow configuration from __main__.py
logger.remove()


async def serve(custom_user_agent: Optional[str] = None) -> None:
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
                description="Search for packages in package indices (PyPI, npm, crates.io, Terraform Registry)",
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
            Tool(
                name="terraform_module_latest_version",
                description="Get the latest version of a Terraform module",
                inputSchema=TerraformModuleLatestVersion.model_json_schema(),
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
            Prompt(
                name="search_terraform",
                description="Search for Terraform modules in the Terraform Registry",
                arguments=[
                    PromptArgument(
                        name="query",
                        description="Module name or search query",
                        required=True,
                    )
                ],
            ),
            Prompt(
                name="terraform_info",
                description="Get information about a specific Terraform module",
                arguments=[
                    PromptArgument(
                        name="name",
                        description="Module name (format: namespace/name/provider)",
                        required=True,
                    ),
                ],
            ),
            Prompt(
                name="terraform_latest_version",
                description="Get the latest version of a specific Terraform module",
                arguments=[
                    PromptArgument(
                        name="name",
                        description="Module name (format: namespace/name/provider)",
                        required=True,
                    ),
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
            elif args.index == "terraform":
                logger.info(
                    f"Searching Terraform Registry for '{args.query}' (limit={args.limit})"
                )
                results = await search_terraform_modules(args.query, args.limit)
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
            elif args.index == "terraform":
                if args.version:
                    logger.info(
                        "Version-specific info for Terraform modules is not supported yet"
                    )
                info = await get_terraform_module_info(args.name)
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

        elif name == "terraform_module_latest_version":
            try:
                args = TerraformModuleLatestVersion(**arguments)
                logger.debug(f"Validated terraform module latest version args: {args}")
            except ValueError as e:
                logger.error(
                    f"Invalid terraform module latest version parameters: {str(e)}"
                )
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            logger.info(f"Getting latest version for Terraform module {args.name}")

            try:
                info = await get_latest_terraform_module_version(args.name)
                logger.info(
                    f"Successfully retrieved latest version for Terraform module {args.name}"
                )
                return [
                    TextContent(
                        type="text",
                        text=f"Latest version for Terraform module {args.name}:\n{json.dumps(info, indent=2)}",
                    )
                ]
            except McpError as e:
                logger.error(
                    f"Error getting latest version for Terraform module: {str(e)}"
                )
                raise

        logger.error(f"Unknown tool: {name}")
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Unknown tool: {name}"))

    @server.get_prompt()
    async def get_prompt(name: str, arguments: Optional[dict]) -> GetPromptResult:
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

        elif name == "search_terraform":
            if not arguments or "query" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Search query is required")
                )

            query = arguments["query"]
            try:
                results = await search_terraform_modules(query, 5)
                return GetPromptResult(
                    description=f"Search results for '{query}' on Terraform Registry",
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

        elif name == "terraform_info":
            if not arguments or "name" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Module name is required")
                )

            module_name = arguments["name"]

            try:
                info = await get_terraform_module_info(module_name)
                return GetPromptResult(
                    description=f"Information for {module_name} on Terraform Registry",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Module information:\n{json.dumps(info, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to get information for {module_name}",
                    messages=[
                        PromptMessage(
                            role="user", content=TextContent(type="text", text=str(e))
                        )
                    ],
                )

        elif name == "terraform_latest_version":
            if not arguments or "name" not in arguments:
                raise McpError(
                    ErrorData(code=INVALID_PARAMS, message="Module name is required")
                )

            module_name = arguments["name"]

            try:
                info = await get_latest_terraform_module_version(module_name)
                return GetPromptResult(
                    description=f"Latest version for {module_name} on Terraform Registry",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Latest version information:\n{json.dumps(info, indent=2)}",
                            ),
                        )
                    ],
                )
            except McpError as e:
                return GetPromptResult(
                    description=f"Failed to get latest version for {module_name}",
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
