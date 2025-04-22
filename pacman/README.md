# Pacman MCP Server

A Model Context Protocol server that provides package index querying capabilities. This server enables LLMs to search and retrieve information from package repositories like PyPI, npm, and crates.io.

### Available Tools

- `search_package` - Search for packages in package indices
    - `index` (string, required): Package index to search ("pypi", "npm", "crates")
    - `query` (string, required): Package name or search query
    - `limit` (integer, optional): Maximum number of results to return (default: 5, max: 50)

- `package_info` - Get detailed information about a specific package
    - `index` (string, required): Package index to query ("pypi", "npm", "crates")
    - `name` (string, required): Package name
    - `version` (string, optional): Specific version to get info for (default: latest)

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
python -m src
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
    "args": ["run", "-i", "--rm", "mcp/pacman"]
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
    "args": ["-m", "src"]
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
        "args": ["run", "-i", "--rm", "mcp/pacman"]
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

## Debugging

You can use the MCP inspector to debug the server. For uvx installations:

```
npx @modelcontextprotocol/inspector uvx mcp-server-pacman
```

Or if you've installed the package in a specific directory or are developing on it:

```
cd path/to/pacman
npx @modelcontextprotocol/inspector uv run mcp-server-pacman
```

## Contributing

We encourage contributions to help expand and improve mcp-server-pacman. Whether you want to add new package indices, enhance existing functionality, or improve documentation, your input is valuable.

For examples of other MCP servers and implementation patterns, see:
https://github.com/modelcontextprotocol/servers

Pull requests are welcome! Feel free to contribute new ideas, bug fixes, or enhancements to make mcp-server-pacman even more powerful and useful.

## License

mcp-server-pacman is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.