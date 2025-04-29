"""Pydantic models for package index API requests."""

from typing import Annotated, Optional, Literal
from pydantic import BaseModel, Field


class PackageSearch(BaseModel):
    """Parameters for searching a package index."""

    index: Annotated[
        Literal["pypi", "npm", "crates", "terraform"],
        Field(description="Package index to search (pypi, npm, crates, terraform)"),
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
        Literal["pypi", "npm", "crates", "terraform"],
        Field(description="Package index to query (pypi, npm, crates, terraform)"),
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


class TerraformModuleLatestVersion(BaseModel):
    """Parameters for getting the latest version of a Terraform module."""

    name: Annotated[
        str, Field(description="Module name (format: namespace/name/provider)")
    ]
