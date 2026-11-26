"""Reusable decorators: timing, logging, retry with backoff, rate limiting.

Each one works on both normal functions and `async def` coroutines, so the
same decorator can wrap an HTTP call or a file write.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger("jobhunt")


def _name(func: Callable[..., Any], args: tuple[Any, ...]) -> str:
    """Readable label: 'RemotiveSource.fetch' instead of just 'fetch'."""
    owner = args[0] if args and hasattr(args[0], "__class__") else None
    if owner is not None and hasattr(owner, func.__name__):
        return f"{owner.__class__.__name__}.{func.__name__}"
    return func.__qualname__


def timer(func: F) -> F:
    """Log how long the call took."""
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                logger.info("%s took %.2fs", _name(func, args), time.perf_counter() - start)

        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            logger.info("%s took %.2fs", _name(func, args), time.perf_counter() - start)

    return wrapper  # type: ignore[return-value]


def log_call(func: F) -> F:
    """Log entry, and log (then re-raise) any exception."""
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.debug("-> %s", _name(func, args))
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                logger.warning("%s failed: %s", _name(func, args), exc)
                raise

        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.debug("-> %s", _name(func, args))
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.warning("%s failed: %s", _name(func, args), exc)
            raise

    return wrapper  # type: ignore[return-value]


def retry(
    attempts: int = 3,
    base_delay: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Retry with exponential backoff (0.5s, 1s, 2s...). Decorator factory."""

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                for attempt in range(1, attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as exc:
                        if attempt == attempts:
                            raise
                        delay = base_delay * 2 ** (attempt - 1)
                        logger.info(
                            "%s attempt %d/%d failed (%s), retrying in %.1fs",
                            _name(func, args), attempt, attempts, exc, delay,
                        )
                        await asyncio.sleep(delay)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == attempts:
                        raise
                    time.sleep(base_delay * 2 ** (attempt - 1))

        return wrapper  # type: ignore[return-value]

    return decorator


def rate_limit(calls_per_second: float) -> Callable[[F], F]:
    """Space out async calls so we stay polite to free public APIs.

    The limit is per object (per job board), so different boards are still
    called in parallel while each single board is never hammered.
    """
    min_interval = 1.0 / calls_per_second

    def decorator(func: F) -> F:
        locks: dict[int, asyncio.Lock] = {}
        last_call: dict[int, float] = {}

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = id(args[0]) if args else 0
            lock = locks.setdefault(key, asyncio.Lock())
            async with lock:
                wait = min_interval - (time.monotonic() - last_call.get(key, 0.0))
                if wait > 0:
                    await asyncio.sleep(wait)
                last_call[key] = time.monotonic()
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
