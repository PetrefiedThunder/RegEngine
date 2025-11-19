"""Authentication routes for token generation and user management."""

from __future__ import annotations

import os
import sys
from datetime import timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

# Add common module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../common"))
from auth import create_access_token, get_current_user, verify_password

logger = structlog.get_logger("auth")
router = APIRouter(prefix="/auth", tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class Token(BaseModel):
    """Token response model"""

    access_token: str
    token_type: str
    expires_in: int


class UserCredentials(BaseModel):
    """User credentials for authentication"""

    username: str
    password: str


# Mock user database (in production, use real database)
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "email": "admin@regengine.io",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "disabled": False,
        "scopes": ["ingest:write", "ingest:read", "opportunities:read", "opportunities:write", "admin"],
    },
    "api_user": {
        "username": "api_user",
        "email": "api@regengine.io",
        "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqRkqTvG9q",  # "password"
        "disabled": False,
        "scopes": ["ingest:write", "ingest:read", "opportunities:read"],
    },
}


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate user against database"""
    user = FAKE_USERS_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


@router.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """
    OAuth2 compatible token generation endpoint.

    Use this endpoint to get an access token:
    - username: Your username
    - password: Your password

    Returns a JWT token that must be included in subsequent requests.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning("authentication_failed", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["username"], "scopes": user["scopes"]},
        expires_delta=access_token_expires,
    )

    logger.info("token_generated", username=user["username"])

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,  # 30 minutes in seconds
    )


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """Get current authenticated user information"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "scopes": current_user.scopes,
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user=Depends(get_current_user)):
    """
    Refresh an existing token.

    Requires a valid token in the Authorization header.
    Returns a new token with extended expiration.
    """
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": current_user.username, "scopes": current_user.scopes},
        expires_delta=access_token_expires,
    )

    logger.info("token_refreshed", username=current_user.username)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,
    )
