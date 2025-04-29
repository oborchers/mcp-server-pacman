"""Utility functions for tests."""

import asyncio


def async_test(coroutine):
    """Helper decorator to run async tests properly."""

    def wrapper(*args, **kwargs):
        asyncio.run(coroutine(*args, **kwargs))

    return wrapper
