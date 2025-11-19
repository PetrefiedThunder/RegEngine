"""
JWT Authentication Module for RegEngine v2
Provides secure API authentication with token-based access control.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """JWT token payload data"""

    username: Optional[str] = None
    scopes: list[str] = []


class User(BaseModel):
    """User model"""

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    scopes: list[str] = []


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token string

    Returns:
        TokenData with username and scopes

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=scopes)
        return token_data
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    FastAPI dependency to get the current authenticated user

    Args:
        credentials: HTTP Bearer token from request header

    Returns:
        User object for the authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = decode_access_token(token)

    # In production, fetch user from database
    # For now, return a mock user
    user = User(
        username=token_data.username,
        scopes=token_data.scopes,
        disabled=False,
    )

    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def require_scope(required_scope: str):
    """
    FastAPI dependency factory to require specific scope

    Args:
        required_scope: The scope required to access the endpoint

    Returns:
        Dependency function that validates scope
    """
    async def scope_checker(current_user: User = Depends(get_current_user)) -> User:
        if required_scope not in current_user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}",
            )
        return current_user

    return scope_checker


# Optional: API Key authentication (simpler alternative to JWT)
class APIKeyAuth:
    """Simple API Key authentication"""

    def __init__(self):
        # In production, store API keys in database with hashing
        self.valid_api_keys = set(
            os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []
        )

    async def __call__(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> str:
        """Validate API key from Bearer token"""
        api_key = credentials.credentials

        if not self.valid_api_keys or api_key not in self.valid_api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return api_key


# Singleton instance for API key auth
api_key_auth = APIKeyAuth()
