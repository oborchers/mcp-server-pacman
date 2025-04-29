"""Caching utilities for HTTP requests."""

import asyncio
import time
import traceback
from functools import wraps
from cachetools import TTLCache
from loguru import logger

# HTTP request cache (maxsize=500, ttl=1 hour)
_http_cache = TTLCache(maxsize=500, ttl=3600)
_cache_lock = asyncio.Lock()
_cache_stats = {"hits": 0, "misses": 0, "bypasses": 0, "total_calls": 0}

# Flag to disable caching in tests
ENABLE_CACHE = True


def async_cached(cache):
    """Decorator to cache results of async functions.

    Since cachetools doesn't natively support async functions, we need
    a custom decorator that handles the async/await pattern.

    Features:
    - Tracks cache hits/misses/bypasses for better observability
    - Thread-safe with asyncio lock for concurrent access
    - Configurable bypass for testing
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            args_repr = (
                f"({args[1:] if args else ''}{', ' if args and kwargs else ''}{kwargs})"
            )
            func_repr = f"{func.__name__}{args_repr}"

            # Update total calls statistic
            async with _cache_lock:
                _cache_stats["total_calls"] += 1

            # Check if caching should be bypassed
            bypass_cache = kwargs.pop("_bypass_cache", False)
            if bypass_cache or not ENABLE_CACHE:
                logger.debug(f"Cache bypassed for {func_repr}")

                # Update bypass statistic
                async with _cache_lock:
                    _cache_stats["bypasses"] += 1

                # Execute function without caching
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    logger.debug(
                        f"Executed {func_repr} in {execution_time:.4f}s (cache bypassed)"
                    )
                    return result
                except Exception as e:
                    logger.error(f"Error executing {func_repr}: {str(e)}")
                    logger.debug(f"Exception details: {traceback.format_exc()}")
                    raise

            # Create a cache key from the function name and arguments
            key = str(args) + str(kwargs)

            # Check if the result is already in the cache
            if key in cache:
                # Update hit statistic
                async with _cache_lock:
                    _cache_stats["hits"] += 1

                execution_time = time.time() - start_time
                logger.info(f"Cache HIT for {func_repr} in {execution_time:.4f}s")
                logger.debug(f"Cache stats: {_cache_stats}")
                return cache[key]

            # Update miss statistic
            async with _cache_lock:
                _cache_stats["misses"] += 1

            logger.info(f"Cache MISS for {func_repr}")

            # Call the original function
            try:
                result = await func(*args, **kwargs)

                # Update the cache with the result (with lock to avoid race conditions)
                async with _cache_lock:
                    cache[key] = result

                execution_time = time.time() - start_time
                logger.info(
                    f"Cached result for {func_repr} (executed in {execution_time:.4f}s)"
                )
                logger.debug(
                    f"Cache size: {len(cache)}/{cache.maxsize}, TTL: {cache.ttl}s"
                )
                return result

            except Exception as e:
                logger.error(f"Error executing {func_repr}: {str(e)}")
                logger.debug(f"Exception details: {traceback.format_exc()}")
                raise

        return wrapper

    return decorator


# Export the HTTP cache for use by provider modules
http_cache = _http_cache
