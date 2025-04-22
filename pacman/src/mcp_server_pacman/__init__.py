from .server import serve


def main():
    """MCP Pacman Server - Package index search functionality for MCP"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="give a model the ability to search package indices like PyPI, npm, and crates.io"
    )
    parser.add_argument("--user-agent", type=str, help="Custom User-Agent string")

    args = parser.parse_args()
    asyncio.run(serve(args.user_agent))


if __name__ == "__main__":
    main()
