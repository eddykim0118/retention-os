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
        get_reviewed_account_ids,
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
        get_reviewed_account_ids,
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
    )


router = APIRouter(prefix="/api", tags=["accounts"])


# =============================================================================
# LOGGING HELPER
# =============================================================================
def log(message: str, level: str = "INFO"):
    """Print a formatted log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {
        "INFO": "📋",
        "START": "🚀",
        "AI": "🤖",
        "SLACK": "💬",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ACTION": "⚡",
        "DEMO": "🎬",
    }.get(level, "📋")
    print(f"[{timestamp}] {prefix} {message}")


# =============================================================================
# DEMO MODE - For live demo to judges
# =============================================================================
# When True, /api/accounts returns empty until "Run Daily Review" is clicked.
# This creates a "fresh start" experience for demos.
DEMO_MODE_ACTIVE = True
log("Demo mode ACTIVE - dashboard will show empty until 'Run Daily Review' is clicked", "DEMO")


@router.get("/accounts", response_model=list[AccountSummary])
async def list_accounts():
    """
    List all accounts with their health scores and status.

    This is used by the Dashboard to show the account table.
    """
    global DEMO_MODE_ACTIVE

    # Demo mode: return empty list until review is run
    if DEMO_MODE_ACTIVE:
        log("GET /api/accounts → Demo mode active, returning empty list", "DEMO")
        return []

    log("GET /api/accounts → Loading accounts from database...", "INFO")
    accounts = get_all_accounts()
    log(f"GET /api/accounts → Found {len(accounts)} accounts", "INFO")
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
    log("=" * 60, "START")
    log("RUN DAILY REVIEW - Starting AI review process", "START")
    log(f"Configuration: USE_REAL_AI={USE_REAL_AI}, MAX_ACCOUNTS={MAX_ACCOUNTS_TO_ANALYZE}", "INFO")
    log("=" * 60, "START")

    async def event_stream():
        global DEMO_MODE_ACTIVE  # Declare at the top of the function

        # 1. Scan all accounts
        log("Step 1: Scanning all accounts from database...", "INFO")
        yield _sse_event({
            "type": "progress",
            "message": "Scanning accounts..."
        })
        await asyncio.sleep(0.5)  # Small delay for UI effect

        accounts = get_all_accounts()
        log(f"Step 1: Found {len(accounts)} total accounts", "SUCCESS")
        yield _sse_event({
            "type": "progress",
            "message": f"Found {len(accounts)} total accounts"
        })
        await asyncio.sleep(0.3)

        # 2. Find at-risk accounts
        log("Step 2: Identifying at-risk accounts (health score < 70)...", "INFO")
        at_risk = get_at_risk_accounts(accounts, threshold=70)
        log(f"Step 2: Found {len(at_risk)} at-risk accounts total", "WARNING")

        # 2.5. Filter out accounts that have already been reviewed
        # This ensures subsequent runs analyze NEW accounts, not the same ones
        reviewed_ids = get_reviewed_account_ids()
        unreviewed_at_risk = [a for a in at_risk if a["account_id"] not in reviewed_ids]
        log(f"Step 2.5: {len(reviewed_ids)} already reviewed, {len(unreviewed_at_risk)} remaining to analyze", "INFO")

        if not unreviewed_at_risk:
            log("All at-risk accounts have been reviewed!", "SUCCESS")
            yield _sse_event({
                "type": "progress",
                "message": f"All {len(at_risk)} at-risk accounts have already been reviewed!"
            })
            await asyncio.sleep(0.3)
            yield _sse_event({
                "type": "complete",
                "message": "No new accounts to analyze. All at-risk accounts have been reviewed.",
                "auto_executed": 0,
                "needs_approval": 0
            })
            DEMO_MODE_ACTIVE = False
            return

        yield _sse_event({
            "type": "progress",
            "message": f"Found {len(unreviewed_at_risk)} unreviewed at-risk accounts, analyzing top {min(len(unreviewed_at_risk), MAX_ACCOUNTS_TO_ANALYZE)}..."
        })
        await asyncio.sleep(0.3)

        # 3. Analyze top N at-risk accounts (from unreviewed list)
        top_accounts = unreviewed_at_risk[:MAX_ACCOUNTS_TO_ANALYZE]
        log(f"Step 3: Will analyze top {len(top_accounts)} accounts", "INFO")
        needs_approval = 0  # All accounts need approval now

        for i, account in enumerate(top_accounts):
            account_name = account.get("account_name", "Unknown")
            account_id = account["account_id"]
            health_score = account["health_score"]
            risk_reasons = account.get("risk_reasons", [])
            arr = _safe_float(account.get("arr_amount")) or 0

            log("-" * 50, "INFO")
            log(f"Analyzing account {i+1}/{len(top_accounts)}: {account_name}", "AI")
            log(f"  Health Score: {health_score}, ARR: ${arr:,.0f}", "INFO")

            # Send "analyzing" event
            yield _sse_event({
                "type": "analyzing",
                "account": account_name,
                "index": i + 1,
                "total": len(top_accounts)
            })
            await asyncio.sleep(0.5)

            # Build signals and run AI analysis
            log(f"  Building account signals for Claude...", "AI")
            signals = build_account_signals(account, health_score, risk_reasons)

            if USE_REAL_AI:
                log(f"  Calling Claude API (real AI)...", "AI")
                analysis = analyze_account(signals)
                if analysis:
                    log(f"  Claude response received!", "SUCCESS")
                    log(f"  → Recommended action: {analysis.get('next_best_action')}", "AI")
                else:
                    log(f"  Claude API failed, falling back to mock", "WARNING")
                    analysis = mock_analyze_account(signals)
            else:
                log(f"  Using mock analysis (USE_REAL_AI=False)", "INFO")
                analysis = mock_analyze_account(signals)
                await asyncio.sleep(1)  # Simulate AI thinking time

            # Determine autonomy level (always needs_approval now - human in the loop)
            autonomy_level, autonomy_reason = get_autonomy_level(health_score, arr)
            log(f"  Autonomy level: {autonomy_level} (all accounts require approval)", "INFO")

            # Build the Slack notification message
            slack_msg = format_slack_alert_message(
                account_name=account_name,
                health_score=health_score,
                action=analysis.get("next_best_action", "training_call"),
                reasoning=analysis.get("action_reasoning", ""),
                urgency=analysis.get("urgency_deadline", "Review soon")
            )

            analysis["slack_message"] = slack_msg

            # Save the review result - all accounts need approval
            save_review_result(account_id, health_score, analysis, autonomy_level, "needs_approval")
            log(f"  Saved review result to database", "SUCCESS")

            # Send Slack notification (but don't execute actions - those need approval)
            log(f"  Sending Slack notification to #retention-alerts", "SLACK")
            result = send_slack_alert("alerts", slack_msg)
            log_action(account_id, "slack_alert", "#retention-alerts", result["success"])

            if result["success"]:
                log(f"  Slack notification sent successfully!", "SUCCESS")
            else:
                log(f"  Slack notification failed: {result.get('detail')}", "WARNING")

            yield _sse_event({
                "type": "warning",
                "account": account_name,
                "action": "needs_approval",
                "message": f"⚠️ {account_name} ready for review — ${arr:,.0f} ARR"
            })
            needs_approval += 1

            await asyncio.sleep(0.3)

        # 4. Complete - disable demo mode so accounts are now visible
        log("=" * 60, "SUCCESS")
        log(f"REVIEW COMPLETE!", "SUCCESS")
        log(f"  Accounts analyzed: {needs_approval} (all require approval)", "WARNING")
        log("=" * 60, "SUCCESS")

        DEMO_MODE_ACTIVE = False
        log("Demo mode DISABLED - dashboard will now show all accounts", "DEMO")

        yield _sse_event({
            "type": "complete",
            "message": f"Review complete. {needs_approval} accounts ready for approval.",
            "auto_executed": 0,
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
    log("=" * 60, "ACTION")
    log(f"HUMAN APPROVAL - Account: {account_id}", "ACTION")
    log("=" * 60, "ACTION")

    # Get the account
    account = get_account_by_id(account_id)
    if not account:
        log(f"Account {account_id} not found!", "WARNING")
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    # Get the latest review
    review = get_latest_review(account_id)
    if not review:
        log(f"No pending review found for {account_id}", "WARNING")
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

    log(f"Approving action for {account_name} (${arr:,.0f} ARR)", "ACTION")
    log(f"Recommended action: {review.get('next_best_action')}", "INFO")

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
        log(f"Sending approval notification to #retention-urgent", "SLACK")
        slack_msg = f"✅ *APPROVED*: Action for {account_name} (${arr:,.0f} ARR)\n\n"
        slack_msg += f"Action: {review.get('next_best_action', 'N/A')}\n"
        slack_msg += f"Approved actions: {', '.join(selected_actions)}\n"
        slack_msg += f"Approved at: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        result = send_slack_alert("urgent", slack_msg)
        log_action(account_id, "approved", "#retention-urgent", result["success"])

        if result["success"]:
            log(f"Approval notification sent successfully!", "SUCCESS")
        else:
            log(f"Approval notification failed: {result.get('detail')}", "WARNING")

        update_review_status(account_id, "approved")
        log(f"Account status updated to 'approved'", "SUCCESS")
        log(f"APPROVAL COMPLETE for {account_name}", "SUCCESS")
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


# =============================================================================
# DEMO RESET ENDPOINT
# =============================================================================

@router.post("/reset")
async def reset_demo():
    """
    Reset the demo to fresh state.

    Call this before starting a new demo to the judges.
    It resets the system to show empty dashboard until "Run Daily Review" is clicked.
    """
    log("=" * 60, "DEMO")
    log("DEMO RESET - Resetting to fresh state", "DEMO")
    log("=" * 60, "DEMO")

    global DEMO_MODE_ACTIVE
    DEMO_MODE_ACTIVE = True

    log("Demo mode ACTIVE - dashboard will show empty until review is run", "DEMO")

    return {
        "status": "reset",
        "message": "Demo mode activated. Dashboard will show empty until 'Run Daily Review' is clicked.",
        "demo_mode": DEMO_MODE_ACTIVE
    }
