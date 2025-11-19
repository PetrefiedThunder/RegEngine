"""
Redis-based rate limiting for RegEngine v2
Implements token bucket algorithm for API rate limiting.
"""

import os
import time
from typing import Optional

import redis
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class RateLimiter:
    """
    Token bucket rate limiter using Redis

    Supports per-user and per-IP rate limiting with configurable
    limits and time windows.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_limit: int = 100,
        default_window: int = 60,
    ):
        """
        Initialize rate limiter

        Args:
            redis_url: Redis connection URL (default: from env REDIS_URL)
            default_limit: Default requests per window
            default_window: Time window in seconds
        """
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self.default_limit = default_limit
        self.default_window = default_window

        try:
            self.redis_client = redis.from_url(
                self.redis_url, decode_responses=True, socket_connect_timeout=1
            )
            # Test connection
            self.redis_client.ping()
        except redis.RedisError as e:
            # Fallback to no-op if Redis unavailable (for development)
            print(f"Warning: Redis unavailable ({e}). Rate limiting disabled.")
            self.redis_client = None

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for rate limit tracking"""
        return f"ratelimit:{endpoint}:{identifier}"

    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> tuple[bool, dict]:
        """
        Check if request should be rate limited

        Args:
            identifier: User ID or IP address
            endpoint: API endpoint path
            limit: Requests allowed per window (overrides default)
            window: Time window in seconds (overrides default)

        Returns:
            Tuple of (allowed: bool, headers: dict)
            headers contain X-RateLimit-* information
        """
        if self.redis_client is None:
            # Redis unavailable, allow all requests
            return True, {}

        limit = limit or self.default_limit
        window = window or self.default_window

        key = self._get_key(identifier, endpoint)
        now = int(time.time())
        window_start = now - window

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Remove requests outside the current window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request with timestamp as score
            pipe.zadd(key, {str(now): now})

            # Set expiration to prevent key buildup
            pipe.expire(key, window)

            results = pipe.execute()
            current_count = results[1]

            # Calculate rate limit headers
            remaining = max(0, limit - current_count - 1)
            reset_time = now + window

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
            }

            if current_count >= limit:
                headers["Retry-After"] = str(window)
                return False, headers

            return True, headers

        except redis.RedisError as e:
            # If Redis fails, allow request but log error
            print(f"Rate limit check failed: {e}")
            return True, {}

    async def rate_limit_middleware(self, request: Request, call_next):
        """
        FastAPI middleware for rate limiting

        Usage:
            app.middleware("http")(rate_limiter.rate_limit_middleware)
        """
        # Skip rate limiting for health/metrics endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get identifier (user from auth or IP address)
        identifier = None

        # Try to get user from auth token
        if hasattr(request.state, "user"):
            identifier = request.state.user.username
        else:
            # Fall back to IP address
            identifier = request.client.host if request.client else "unknown"

        endpoint = request.url.path

        # Check rate limit
        allowed, headers = self.check_rate_limit(identifier, endpoint)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": headers.get("Retry-After"),
                },
                headers=headers,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response


def get_rate_limiter(
    limit: int = 100, window: int = 60
) -> RateLimiter:
    """
    Get a configured rate limiter instance

    Args:
        limit: Requests per window
        window: Time window in seconds

    Returns:
        RateLimiter instance
    """
    return RateLimiter(default_limit=limit, default_window=window)


# Dependency for per-endpoint rate limiting
async def rate_limit_dependency(
    request: Request,
    limit: int = 100,
    window: int = 60,
):
    """
    FastAPI dependency for rate limiting specific endpoints

    Usage:
        @app.get("/endpoint", dependencies=[Depends(rate_limit_dependency)])
    """
    rate_limiter = get_rate_limiter(limit, window)

    # Get identifier
    identifier = request.client.host if request.client else "unknown"

    allowed, headers = rate_limiter.check_rate_limit(
        identifier, request.url.path, limit, window
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers=headers,
        )
