"""MCP Server for package index searching capabilities.

This package provides a Model Context Protocol (MCP) server that enables
querying package repositories like PyPI, npm, crates.io, and Docker Hub.
"""

import sys
import asyncio
import argparse
from loguru import logger
from .server import serve


# For backward compatibility, re-export all model classes
from .models import PackageSearch, PackageInfo, DockerImageSearch, DockerImageInfo

# For backward compatibility, re-export all provider functions
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
)

# For backward compatibility, re-export utility functions
from .utils import ENABLE_CACHE, DEFAULT_USER_AGENT


__all__ = [
    "serve",
    "main",
    "PackageSearch",
    "PackageInfo",
    "DockerImageSearch",
    "DockerImageInfo",
    "search_pypi",
    "get_pypi_info",
    "search_npm",
    "get_npm_info",
    "search_crates",
    "get_crates_info",
    "search_docker_hub",
    "get_docker_hub_tags",
    "get_docker_hub_tag_info",
    "ENABLE_CACHE",
    "DEFAULT_USER_AGENT",
]


def main():
    """MCP Pacman Server - Package index search functionality for MCP"""
    parser = argparse.ArgumentParser(
        description="give a model the ability to search package indices like PyPI, npm, and crates.io"
    )
    parser.add_argument("--user-agent", type=str, help="Custom User-Agent string")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging level based on arguments
    log_level = "DEBUG" if args.debug else "INFO"
    logger.configure(
        handlers=[
            {
                "sink": sys.stderr,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                "level": log_level,
            }
        ]
    )

    logger.info(f"Starting mcp-pacman server with logging level: {log_level}")

    try:
        asyncio.run(serve(args.user_agent))
    except KeyboardInterrupt:
        logger.info("Server interrupted by keyboard interrupt")
    except Exception as e:
        logger.exception(f"Server failed with error: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()
