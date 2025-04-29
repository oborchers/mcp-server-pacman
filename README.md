![Pacman Logo](media/logo.png)

# Pacman MCP Server

A Model Context Protocol server that provides package index querying capabilities. This server enables LLMs to search and retrieve information from package repositories like PyPI, npm, crates.io, Docker Hub, and Terraform Registry.

<a href="https://glama.ai/mcp/servers/@oborchers/mcp-server-pacman">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@oborchers/mcp-server-pacman/badge" alt="mcp-server-pacman MCP server" />
</a>

### Available Tools

- `search_package` - Search for packages in package indices
    - `index` (string, required): Package index to search ("pypi", "npm", "crates", "terraform")
    - `query` (string, required): Package name or search query
    - `limit` (integer, optional): Maximum number of results to return (default: 5, max: 50)

- `package_info` - Get detailed information about a specific package
    - `index` (string, required): Package index to query ("pypi", "npm", "crates", "terraform")
    - `name` (string, required): Package name
    - `version` (string, optional): Specific version to get info for (default: latest)

- `search_docker_image` - Search for Docker images in Docker Hub
    - `query` (string, required): Image name or search query
    - `limit` (integer, optional): Maximum number of results to return (default: 5, max: 50)

- `docker_image_info` - Get detailed information about a specific Docker image
    - `name` (string, required): Image name (e.g., user/repo or library/repo)
    - `tag` (string, optional): Specific image tag (default: latest)
    
- `terraform_module_latest_version` - Get the latest version of a Terraform module
    - `name` (string, required): Module name (format: namespace/name/provider)

### Prompts

- **search_pypi**
  - Search for Python packages on PyPI
  - Arguments:
    - `query` (string, required): Package name or search query

- **pypi_info**
  - Get information about a specific Python package
  - Arguments:
    - `name` (string, required): Package name
    - `version` (string, optional): Specific version

- **search_npm**
  - Search for JavaScript packages on npm
  - Arguments:
    - `query` (string, required): Package name or search query

- **npm_info**
  - Get information about a specific JavaScript package
  - Arguments:
    - `name` (string, required): Package name
    - `version` (string, optional): Specific version

- **search_crates**
  - Search for Rust packages on crates.io
  - Arguments:
    - `query` (string, required): Package name or search query

- **crates_info**
  - Get information about a specific Rust package
  - Arguments:
    - `name` (string, required): Package name
    - `version` (string, optional): Specific version
    
- **search_docker**
  - Search for Docker images on Docker Hub
  - Arguments:
    - `query` (string, required): Image name or search query

- **docker_info**
  - Get information about a specific Docker image
  - Arguments:
    - `name` (string, required): Image name (e.g., user/repo)
    - `tag` (string, optional): Specific tag
    
- **search_terraform**
  - Search for Terraform modules in the Terraform Registry
  - Arguments:
    - `query` (string, required): Module name or search query

- **terraform_info**
  - Get information about a specific Terraform module
  - Arguments:
    - `name` (string, required): Module name (format: namespace/name/provider)
    
- **terraform_latest_version**
  - Get the latest version of a specific Terraform module
  - Arguments:
    - `name` (string, required): Module name (format: namespace/name/provider)

## Installation

### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *mcp-server-pacman*.

### Using PIP

Alternatively you can install `mcp-server-pacman` via pip:

```
pip install mcp-server-pacman
```

After installation, you can run it as a script using:

```
python -m mcp_server_pacman
```

### Using Docker

You can also use the Docker image:

```
docker pull oborchers/mcp-server-pacman:latest
docker run -i --rm oborchers/mcp-server-pacman
```

## Configuration

### Configure for Claude.app

Add to your Claude settings:

<details>
<summary>Using uvx</summary>

```json
"mcpServers": {
  "pacman": {
    "command": "uvx",
    "args": ["mcp-server-pacman"]
  }
}
```
</details>

<details>
<summary>Using docker</summary>

```json
"mcpServers": {
  "pacman": {
    "command": "docker",
    "args": ["run", "-i", "--rm", "oborchers/mcp-server-pacman:latest"]
  }
}
```
</details>

<details>
<summary>Using pip installation</summary>

```json
"mcpServers": {
  "pacman": {
    "command": "python",
    "args": ["-m", "mcp-server-pacman"]
  }
}
```
</details>

### Configure for VS Code

For manual installation, add the following JSON block to your User Settings (JSON) file in VS Code. You can do this by pressing `Ctrl + Shift + P` and typing `Preferences: Open User Settings (JSON)`.

Optionally, you can add it to a file called `.vscode/mcp.json` in your workspace. This will allow you to share the configuration with others.

> Note that the `mcp` key is needed when using the `mcp.json` file.

<details>
<summary>Using uvx</summary>

```json
{
  "mcp": {
    "servers": {
      "pacman": {
        "command": "uvx",
        "args": ["mcp-server-pacman"]
      }
    }
  }
}
```
</details>

<details>
<summary>Using Docker</summary>

```json
{
  "mcp": {
    "servers": {
      "pacman": {
        "command": "docker",
        "args": ["run", "-i", "--rm", "oborchers/mcp-server-pacman:latest"]
      }
    }
  }
}
```
</details>

### Customization - User-agent

By default, the server will use the user-agent:
```
ModelContextProtocol/1.0 Pacman (+https://github.com/modelcontextprotocol/servers)
```

This can be customized by adding the argument `--user-agent=YourUserAgent` to the `args` list in the configuration.

## Development

### Running Tests

- Run all tests:
  ```
  uv run pytest -xvs
  ```

- Run specific test categories:
  ```
  # Run all provider tests
  uv run pytest -xvs tests/providers/

  # Run integration tests for a specific provider
  uv run pytest -xvs tests/integration/test_pypi_integration.py
  
  # Run specific test class
  uv run pytest -xvs tests/providers/test_npm.py::TestNPMFunctions
  
  # Run a specific test method
  uv run pytest -xvs tests/providers/test_pypi.py::TestPyPIFunctions::test_search_pypi_success
  ```

- Check code style:
  ```
  uv run ruff check .
  uv run ruff format --check .
  ```

- Format code:
  ```
  uv run ruff format .
  ```

### Debugging

You can use the MCP inspector to debug the server. For uvx installations:

```
npx @modelcontextprotocol/inspector uvx mcp-server-pacman
```

Or if you've installed the package in a specific directory or are developing on it:

```
cd path/to/pacman
npx @modelcontextprotocol/inspector uv run mcp-server-pacman
```

## Release Process

The project uses GitHub Actions for automated releases:

1. Update the version in `pyproject.toml`
2. Create a new tag with `git tag vX.Y.Z` (e.g., `git tag v0.1.0`)
3. Push the tag with `git push --tags`

This will automatically:
- Verify the version in `pyproject.toml` matches the tag
- Run tests and lint checks
- Build and publish to PyPI
- Build and publish to Docker Hub as `oborchers/mcp-server-pacman:latest` and `oborchers/mcp-server-pacman:X.Y.Z`

## Project Structure

The codebase is organized into the following structure:

```
src/mcp_server_pacman/
├── models/             # Data models/schemas
├── providers/          # Package registry API clients
│   ├── pypi.py         # PyPI API functions
│   ├── npm.py          # npm API functions
│   ├── crates.py       # crates.io API functions
│   ├── dockerhub.py    # Docker Hub API functions
│   └── terraform.py    # Terraform Registry API functions
├── utils/              # Utilities and helpers
│   ├── cache.py        # Caching functionality
│   ├── constants.py    # Shared constants
│   └── parsers.py      # HTML parsing utilities
├── __init__.py         # Package initialization
├── __main__.py         # Entry point
└── server.py           # MCP server implementation
```

Tests follow a similar structure:

```
tests/
├── integration/        # Integration tests (real API calls)
├── models/             # Model validation tests
├── providers/          # Provider function tests
└── utils/              # Test utilities
```

## Contributing

We encourage contributions to help expand and improve mcp-server-pacman. Whether you want to add new package indices, enhance existing functionality, or improve documentation, your input is valuable.

For examples of other MCP servers and implementation patterns, see:
https://github.com/modelcontextprotocol/servers

Pull requests are welcome! Feel free to contribute new ideas, bug fixes, or enhancements to make mcp-server-pacman even more powerful and useful.

## License

mcp-server-pacman is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.