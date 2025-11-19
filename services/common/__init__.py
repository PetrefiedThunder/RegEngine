"""
RegEngine v2 Common Utilities
Shared modules across all microservices
"""

from .auth import (
    APIKeyAuth,
    User,
    api_key_auth,
    create_access_token,
    decode_access_token,
    get_current_user,
    get_password_hash,
    require_scope,
    verify_password,
)
from .rate_limit import (
    RateLimiter,
    get_rate_limiter,
    rate_limit_dependency,
)

__all__ = [
    "User",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "require_scope",
    "verify_password",
    "get_password_hash",
    "APIKeyAuth",
    "api_key_auth",
    "RateLimiter",
    "get_rate_limiter",
    "rate_limit_dependency",
]
