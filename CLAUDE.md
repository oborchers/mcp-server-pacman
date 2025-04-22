# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Lint/Test Commands
- Run tests: `uv run pytest -xvs tests/`
- Run a single test: `uv run pytest -xvs tests/test_file.py::TestClass::test_method`
- Check formatting: `uv run ruff format --check .`
- Format code: `uv run ruff format .`
- Lint code: `uv run ruff check .`
- Lint and fix: `uv run ruff check --fix .`
- Run server: `uv run python -m src.mcp_server_pacman`
- Run with debug logging: `uv run python -m src.mcp_server_pacman --debug`

## Code Style
- Follow PEP 8 guidelines
- Use type annotations and Pydantic for data validation
- Use async/await for asynchronous operations
- Imports order: standard library, third-party, local
- Exception handling: use custom McpError with appropriate error codes
- Use loguru for logging with appropriate levels
- Use descriptive error messages with context
- Use f-strings for string formatting
- Test code with unittest framework and async helpers