"""Alert Service API Routes"""

from __future__ import annotations

import os
import sys
from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

# Add common module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../common"))
from auth import User, require_scope

logger = structlog.get_logger("alerts")
router = APIRouter()


class AlertSubscription(BaseModel):
    """Alert subscription model"""

    subscription_id: str | None = None
    user_id: str
    email: EmailStr | None = None
    slack_channel: str | None = None
    webhook_url: str | None = None
    triggers: List[str]  # ["amendment", "new_obligation", "threshold_change"]
    jurisdictions: List[str] | None = None
    concepts: List[str] | None = None
    active: bool = True


# In-memory storage (use database in production)
subscriptions: dict[str, AlertSubscription] = {}


@router.get("/health")
def health() -> dict[str, str]:
    """Health check"""
    return {"status": "ok"}


@router.post("/subscriptions", response_model=AlertSubscription)
def create_subscription(
    subscription: AlertSubscription,
    current_user: User = Depends(require_scope("alerts:write")),
) -> AlertSubscription:
    """Create alert subscription"""
    import uuid

    subscription.subscription_id = str(uuid.uuid4())
    subscription.user_id = current_user.username
    subscriptions[subscription.subscription_id] = subscription

    logger.info(
        "subscription_created",
        subscription_id=subscription.subscription_id,
        user=current_user.username,
    )

    return subscription


@router.get("/subscriptions", response_model=List[AlertSubscription])
def list_subscriptions(
    current_user: User = Depends(require_scope("alerts:read")),
) -> List[AlertSubscription]:
    """List user's subscriptions"""
    user_subs = [
        sub for sub in subscriptions.values() if sub.user_id == current_user.username
    ]
    return user_subs


@router.delete("/subscriptions/{subscription_id}")
def delete_subscription(
    subscription_id: str,
    current_user: User = Depends(require_scope("alerts:write")),
) -> dict[str, str]:
    """Delete subscription"""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub = subscriptions[subscription_id]
    if sub.user_id != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized")

    del subscriptions[subscription_id]
    logger.info("subscription_deleted", subscription_id=subscription_id)

    return {"status": "deleted", "subscription_id": subscription_id}


@router.post("/test-alert")
def send_test_alert(
    current_user: User = Depends(require_scope("alerts:write")),
) -> dict[str, str]:
    """Send test alert"""
    logger.info("test_alert_sent", user=current_user.username)
    return {"status": "sent", "message": "Test alert triggered"}
