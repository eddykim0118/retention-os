"""
routes.py - API endpoints

This module defines all the HTTP endpoints that the frontend can call.

Endpoints:
- GET /api/accounts - list all accounts with health scores
- GET /api/accounts/{account_id} - get single account with full details
- POST /api/accounts/{account_id}/approve - approve a pending action
- GET /api/review/run - run AI review with SSE streaming
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

try:
    from database import (
        get_all_accounts,
        get_account_by_id,
        get_latest_review,
        get_action_log,
        save_review_result,
        log_action,
        update_review_status,
    )
    from health_score import (
        calculate_health_score,
        get_risk_level,
        get_autonomy_level,
        get_at_risk_accounts,
    )
    from models import AccountSummary, AccountDetail, ActionTaken, ApproveRequest, ApproveResponse
    from agent import analyze_account, build_account_signals, mock_analyze_account
    from actions import (
        create_linear_ticket,
        format_linear_ticket,
        send_slack_alert,
        send_email,
        format_slack_alert_message,
        format_slack_approval_message,
    )
except ImportError:
    from backend.database import (
        get_all_accounts,
        get_account_by_id,
        get_latest_review,
        get_action_log,
        save_review_result,
        log_action,
        update_review_status,
    )
    from backend.health_score import (
        calculate_health_score,
        get_risk_level,
        get_autonomy_level,
        get_at_risk_accounts,
    )
    from backend.models import AccountSummary, AccountDetail, ActionTaken, ApproveRequest, ApproveResponse
    from backend.agent import analyze_account, build_account_signals, mock_analyze_account
    from backend.actions import (
        create_linear_ticket,
        format_linear_ticket,
        send_slack_alert,
        send_email,
        format_slack_alert_message,
        format_slack_approval_message,
    )


router = APIRouter(prefix="/api", tags=["accounts"])


@router.get("/accounts", response_model=list[AccountSummary])
async def list_accounts():
    """
    List all accounts with their health scores and status.

    This is used by the Dashboard to show the account table.
    """
    accounts = get_all_accounts()
    result = []

    for account in accounts:
        # Calculate health score
        health_score, _ = calculate_health_score(account["account_id"])
        risk_level = get_risk_level(health_score)

        # Get latest review if exists
        review = get_latest_review(account["account_id"])
        action_log = get_action_log(account["account_id"])

        result.append(AccountSummary(
            account_id=account["account_id"],
            account_name=account["account_name"],
            industry=account.get("industry"),
            plan_tier=account.get("plan_tier"),
            health_score=health_score,
            risk_level=risk_level,
            mrr_amount=_safe_float(account.get("mrr_amount")),
            arr_amount=_safe_float(account.get("arr_amount")),
            next_best_action=review.get("next_best_action") if review else None,
            status=review.get("status") if review else None,
            actions_taken=[entry["action_type"] for entry in action_log] or None,
        ))

    # Sort by health score (worst first)
    result.sort(key=lambda x: x.health_score if x.health_score is not None else 100)

    return result


@router.get("/accounts/{account_id}", response_model=AccountDetail)
async def get_account_detail(account_id: str):
    """
    Get detailed information about a single account.

    This includes:
    - Basic account info
    - Health score and risk level
    - AI analysis results (if available)
    - Actions taken
    """
    account = get_account_by_id(account_id)

    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    # Calculate health score
    health_score, risk_reasons = calculate_health_score(account_id)
    risk_level = get_risk_level(health_score)

    # Get autonomy level
    arr = _safe_float(account.get("arr_amount")) or 0
    autonomy_level, autonomy_reason = get_autonomy_level(health_score, arr)

    # Get latest review if exists
    review = get_latest_review(account_id)

    # Get action log
    action_log = get_action_log(account_id)
    actions_taken = [
        ActionTaken(
            type=a["action_type"],
            channel=a.get("action_detail"),
            timestamp=a.get("executed_at"),
            status="sent" if a.get("success") else "failed"
        )
        for a in action_log
    ]
    linear_ticket_title, linear_ticket_description = _build_linear_ticket_preview(
        account_name=account["account_name"],
        health_score=health_score,
        review=review,
        fallback_risk_reasons=risk_reasons,
    )

    return AccountDetail(
        account_id=account["account_id"],
        account_name=account["account_name"],
        industry=account.get("industry"),
        country=account.get("country"),
        plan_tier=account.get("plan_tier"),
        seats=_safe_int(account.get("seats")),
        health_score=health_score,
        risk_level=risk_level,
        mrr_amount=_safe_float(account.get("mrr_amount")),
        arr_amount=_safe_float(account.get("arr_amount")),
        # AI Analysis (from review if exists)
        churn_risk_score=review.get("churn_risk_score") if review else None,
        risk_reasons=risk_reasons if not review else _parse_list(review.get("risk_reasons")),
        next_best_action=review.get("next_best_action") if review else None,
        action_reasoning=review.get("action_reasoning") if review else None,
        why_not_others=review.get("why_not_others") if review else None,
        generated_email=review.get("generated_email") if review else None,
        internal_memo=review.get("internal_memo") if review else None,
        slack_message=review.get("slack_message") if review else None,
        linear_ticket_title=linear_ticket_title,
        linear_ticket_description=linear_ticket_description,
        urgency_deadline=review.get("urgency_deadline") if review else None,
        # Status
        status=review.get("status") if review else None,
        autonomy_level=autonomy_level,
        autonomy_reason=autonomy_reason,
        actions_taken=actions_taken if actions_taken else None,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _safe_float(value) -> Optional[float]:
    """Safely convert value to float, returning None if not possible."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> Optional[int]:
    """Safely convert value to int, returning None if not possible."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_list(value) -> Optional[list[str]]:
    """Parse a string representation of a list back to a list."""
    if not value:
        return None
    if isinstance(value, list):
        return value
    # Handle string representation like "['item1', 'item2']"
    try:
        import ast
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return [value]


def _build_linear_ticket_preview(
    account_name: str,
    health_score: int,
    review: Optional[dict],
    fallback_risk_reasons: list[str],
) -> tuple[Optional[str], Optional[str]]:
    """Build a deterministic Linear ticket preview from the latest review."""
    if not review or not review.get("next_best_action"):
        return None, None

    title, description = format_linear_ticket(
        account_name=account_name,
        health_score=health_score,
        action=review.get("next_best_action"),
        reasoning=review.get("action_reasoning") or "",
        risk_reasons=_parse_list(review.get("risk_reasons")) or fallback_risk_reasons,
        urgency=review.get("urgency_deadline") or "Review soon",
    )
    return title, description


# =============================================================================
# SSE ENDPOINT - AI REVIEW
# =============================================================================

# Configuration
USE_REAL_AI = bool(os.environ.get("ANTHROPIC_API_KEY"))
MAX_ACCOUNTS_TO_ANALYZE = 3  # Limit for demo purposes


def _sse_event(data: dict) -> str:
    """Format data as an SSE event."""
    return f"data: {json.dumps(data)}\n\n"


@router.get("/review/run")
async def run_review():
    """
    Run the AI review process with real-time SSE updates.

    IMPORTANT: This MUST be a GET endpoint because browser's EventSource API
    only supports GET requests.

    SSE Event Types:
    - progress: General progress updates
    - analyzing: Currently analyzing an account
    - action: AI took an action (Slack sent, etc.)
    - complete: Review finished
    """
    async def event_stream():
        # 1. Scan all accounts
        yield _sse_event({
            "type": "progress",
            "message": "Scanning accounts..."
        })
        await asyncio.sleep(0.5)  # Small delay for UI effect

        accounts = get_all_accounts()
        yield _sse_event({
            "type": "progress",
            "message": f"Found {len(accounts)} total accounts"
        })
        await asyncio.sleep(0.3)

        # 2. Find at-risk accounts
        at_risk = get_at_risk_accounts(accounts, threshold=70)
        yield _sse_event({
            "type": "progress",
            "message": f"Identified {len(at_risk)} at-risk accounts, analyzing top {min(len(at_risk), MAX_ACCOUNTS_TO_ANALYZE)}..."
        })
        await asyncio.sleep(0.3)

        # 3. Analyze top N at-risk accounts
        top_accounts = at_risk[:MAX_ACCOUNTS_TO_ANALYZE]
        auto_executed = 0
        needs_approval = 0

        for i, account in enumerate(top_accounts):
            account_name = account.get("account_name", "Unknown")
            account_id = account["account_id"]
            health_score = account["health_score"]
            risk_reasons = account.get("risk_reasons", [])
            arr = _safe_float(account.get("arr_amount")) or 0

            # Send "analyzing" event
            yield _sse_event({
                "type": "analyzing",
                "account": account_name,
                "index": i + 1,
                "total": len(top_accounts)
            })
            await asyncio.sleep(0.5)

            # Build signals and run AI analysis
            signals = build_account_signals(account, health_score, risk_reasons)

            if USE_REAL_AI:
                analysis = analyze_account(signals)
                if not analysis:
                    analysis = mock_analyze_account(signals)
            else:
                analysis = mock_analyze_account(signals)
                await asyncio.sleep(1)  # Simulate AI thinking time

            # Determine autonomy level
            autonomy_level, autonomy_reason = get_autonomy_level(health_score, arr)
            status = "auto_executed" if autonomy_level == "auto" else "needs_approval"

            # Build the exact Slack message that will be sent so the frontend
            # can show the same content in the risk signal preview.
            if autonomy_level == "auto":
                slack_msg = format_slack_alert_message(
                    account_name=account_name,
                    health_score=health_score,
                    action=analysis.get("next_best_action", "training_call"),
                    reasoning=analysis.get("action_reasoning", ""),
                    urgency=analysis.get("urgency_deadline", "Review soon")
                )
            else:
                slack_msg = format_slack_approval_message(
                    account_name=account_name,
                    arr_amount=arr,
                    action=analysis.get("next_best_action", "senior_outreach"),
                    reasoning=analysis.get("action_reasoning", "")
                )

            analysis["slack_message"] = slack_msg

            # Save the review result
            save_review_result(account_id, health_score, analysis, autonomy_level, status)

            # Take action based on autonomy level
            if autonomy_level == "auto":
                # Auto-execute: send Slack alert
                result = send_slack_alert("alerts", slack_msg)
                log_action(account_id, "slack_alert", "#retention-alerts", result["success"])

                yield _sse_event({
                    "type": "action",
                    "account": account_name,
                    "action": "slack_sent",
                    "message": f"✅ Sent Slack alert for {account_name}"
                })
                auto_executed += 1

            else:
                # Needs approval: send to urgent channel
                result = send_slack_alert("urgent", slack_msg)
                log_action(account_id, "slack_urgent", "#retention-urgent", result["success"])

                yield _sse_event({
                    "type": "action",
                    "account": account_name,
                    "action": "needs_approval",
                    "message": f"⚠️ {account_name} needs approval — ${arr:,.0f} ARR at risk"
                })
                needs_approval += 1

            await asyncio.sleep(0.3)

        # 4. Complete
        yield _sse_event({
            "type": "complete",
            "message": f"Review complete. {auto_executed} auto-executed, {needs_approval} need approval.",
            "auto_executed": auto_executed,
            "needs_approval": needs_approval
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# =============================================================================
# APPROVE ENDPOINT
# =============================================================================

@router.post("/accounts/{account_id}/approve", response_model=ApproveResponse)
async def approve_action(account_id: str, request: ApproveRequest):
    """
    Approve a pending action for an account.

    This is called when a human clicks "Approve" on the frontend
    for a high-value account that required approval.
    """
    # Get the account
    account = get_account_by_id(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    # Get the latest review
    review = get_latest_review(account_id)
    if not review:
        raise HTTPException(status_code=400, detail="No review found for this account")

    selected_actions = []
    for action in request.selected_actions:
        if action in {"linear_ticket", "send_email"} and action not in selected_actions:
            selected_actions.append(action)

    if not selected_actions:
        raise HTTPException(status_code=400, detail="No valid manual actions selected")

    account_name = account.get("account_name", "Unknown")
    arr = _safe_float(account.get("arr_amount")) or 0
    health_score = _safe_int(review.get("health_score")) or calculate_health_score(account_id)[0]
    risk_reasons = _parse_list(review.get("risk_reasons")) or []
    executed_at = datetime.now().isoformat()
    executed_actions = []

    if "linear_ticket" in selected_actions:
        title, description = format_linear_ticket(
            account_name=account_name,
            health_score=health_score,
            action=review.get("next_best_action") or "support_escalation",
            reasoning=review.get("action_reasoning") or "",
            risk_reasons=risk_reasons,
            urgency=review.get("urgency_deadline") or "Review soon",
        )
        priority = 1 if health_score < 40 else 2 if health_score <= 70 else 3
        result = create_linear_ticket(title=title, description=description, priority=priority)
        detail_value = result.get("ticket_url") or result.get("detail", "Linear")
        log_action(account_id, "linear_ticket", detail_value, result["success"])
        executed_actions.append(
            ActionTaken(
                type="linear_ticket",
                channel=detail_value,
                timestamp=executed_at,
                status="sent" if result["success"] else "failed",
            )
        )

    if "send_email" in selected_actions:
        email_result = send_email(
            account_name=account_name,
            email_content=review.get("generated_email") or "",
        )
        log_action(account_id, "email_sent", email_result.get("recipient", "TEST_EMAIL"), email_result["success"])
        executed_actions.append(
            ActionTaken(
                type="email_sent",
                channel=email_result.get("recipient"),
                timestamp=executed_at,
                status="sent" if email_result["success"] else "failed",
            )
        )

    response_status = review.get("status") or "pending"
    if review.get("status") == "needs_approval":
        slack_msg = f"✅ *APPROVED*: Action for {account_name} (${arr:,.0f} ARR)\n\n"
        slack_msg += f"Action: {review.get('next_best_action', 'N/A')}\n"
        slack_msg += f"Approved actions: {', '.join(selected_actions)}\n"
        slack_msg += f"Approved at: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        result = send_slack_alert("urgent", slack_msg)
        log_action(account_id, "approved", "#retention-urgent", result["success"])
        update_review_status(account_id, "approved")
        response_status = "approved"
        executed_actions.append(
            ActionTaken(
                type="slack_urgent",
                channel="#retention-urgent",
                timestamp=executed_at,
                status="sent" if result["success"] else "failed",
            )
        )

    return ApproveResponse(
        status=response_status,
        actions_executed=executed_actions,
        approved_at=executed_at,
    )
