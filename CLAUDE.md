# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Lint/Test Commands

- **Install Development Environment**: `cd pacman && uv pip install -e .[dev]`
- **Lint**: `pre-commit run ruff --all-files` (runs both ruff and ruff-format)
- **Run Tests (All)**: `cd pacman && uv run pytest -xvs tests/`
- **Run Single Test**: `cd pacman && uv run pytest -xvs tests/test_server.py::TestClass::test_function`
- **Test with Coverage**: `cd pacman && uv run pytest -xvs tests/ --cov=src --cov-report=term`

## Code Style Guidelines

- **Imports**: Standard library first, then third-party, then local imports; alphabetized within groups
- **Formatting**: 4-space indentation, double quotes for strings, 100 char line length
- **Types**: Always use type annotations; use Pydantic models for validation
- **Naming**: Classes=PascalCase, functions/variables=snake_case, constants=UPPER_SNAKE_CASE
- **Error Handling**: Use McpError with proper error codes and descriptive messages
- **Documentation**: All functions/classes need docstrings with parameter explanations

This is a multi-repo project with separate packages in directories like `pacman/` and `docy/`. Always run commands from the appropriate directory context.