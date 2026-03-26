"""
models.py - Pydantic response models

These models define the shape of data returned by our API.
Think of them as TypeScript interfaces but for Python.

Benefits:
1. Automatic JSON serialization
2. Type validation
3. Auto-generated API documentation
"""

from typing import Optional
from pydantic import BaseModel


class AccountSummary(BaseModel):
    """Summary view of an account - used in the accounts list."""
    account_id: str
    account_name: str
    industry: Optional[str] = None
    plan_tier: Optional[str] = None
    health_score: Optional[int] = None
    risk_level: Optional[str] = None  # "high", "medium", "low"
    mrr_amount: Optional[float] = None
    arr_amount: Optional[float] = None
    next_best_action: Optional[str] = None
    status: Optional[str] = None  # "pending", "auto_executed", "needs_approval", "approved"
    actions_taken: Optional[list[str]] = None


class ActionTaken(BaseModel):
    """Record of an action taken by the AI."""
    type: str  # "slack_alert", "slack_urgent", "email_draft", "linear_ticket"
    channel: Optional[str] = None  # e.g., "#retention-alerts"
    timestamp: Optional[str] = None
    status: str  # "sent", "ready", "failed"


class ApproveRequest(BaseModel):
    """Request body for approving manual follow-up actions."""
    selected_actions: list[str]


class AccountDetail(BaseModel):
    """Full detail view of an account - used in account detail page."""
    account_id: str
    account_name: str
    industry: Optional[str] = None
    country: Optional[str] = None
    plan_tier: Optional[str] = None
    seats: Optional[int] = None
    health_score: Optional[int] = None
    risk_level: Optional[str] = None
    mrr_amount: Optional[float] = None
    arr_amount: Optional[float] = None

    # AI Analysis results
    churn_risk_score: Optional[int] = None
    risk_reasons: Optional[list[str]] = None
    next_best_action: Optional[str] = None
    action_reasoning: Optional[str] = None
    why_not_others: Optional[str] = None
    generated_email: Optional[str] = None
    internal_memo: Optional[str] = None
    slack_message: Optional[str] = None
    linear_ticket_title: Optional[str] = None
    linear_ticket_description: Optional[str] = None
    urgency_deadline: Optional[str] = None

    # Status and actions
    status: Optional[str] = None
    autonomy_level: Optional[str] = None  # "auto" or "needs_approval"
    autonomy_reason: Optional[str] = None
    actions_taken: Optional[list[ActionTaken]] = None


class ApproveResponse(BaseModel):
    """Response from the approve endpoint."""
    status: str
    actions_executed: list[ActionTaken]
    approved_at: str


class SSEEvent(BaseModel):
    """Server-Sent Event data structure."""
    type: str  # "progress", "analyzing", "action", "complete"
    message: Optional[str] = None
    account: Optional[str] = None
    index: Optional[int] = None
    total: Optional[int] = None
    auto_executed: Optional[int] = None
    needs_approval: Optional[int] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
