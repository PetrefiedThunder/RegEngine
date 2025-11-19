"""RegEngine SDK Exceptions"""


class RegEngineError(Exception):
    """Base exception for RegEngine SDK"""
    pass


class AuthenticationError(RegEngineError):
    """Authentication failed"""
    pass


class RateLimitError(RegEngineError):
    """Rate limit exceeded"""
    pass


class NotFoundError(RegEngineError):
    """Resource not found"""
    pass
