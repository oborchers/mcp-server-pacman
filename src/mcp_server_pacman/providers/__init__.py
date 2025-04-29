"""Package index providers for mcp-server-pacman."""

from .pypi import search_pypi, get_pypi_info
from .npm import search_npm, get_npm_info
from .crates import search_crates, get_crates_info
from .dockerhub import search_docker_hub, get_docker_hub_tags, get_docker_hub_tag_info
from .terraform import (
    search_terraform_modules,
    get_terraform_module_info,
    get_latest_terraform_module_version,
)

__all__ = [
    "search_pypi",
    "get_pypi_info",
    "search_npm",
    "get_npm_info",
    "search_crates",
    "get_crates_info",
    "search_docker_hub",
    "get_docker_hub_tags",
    "get_docker_hub_tag_info",
    "search_terraform_modules",
    "get_terraform_module_info",
    "get_latest_terraform_module_version",
]
