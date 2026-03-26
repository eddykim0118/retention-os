"""
health_score.py - Health score calculation and autonomy level logic

This is the "business logic" of the system. It encodes our domain expertise:
- What signals indicate a customer is at risk?
- How much should each signal weigh?
- When should the AI act autonomously vs ask for approval?
"""

try:
    from database import (
        get_usage_trend,
        get_ticket_stats,
        get_account_by_id,
    )
except ImportError:
    from backend.database import (
        get_usage_trend,
        get_ticket_stats,
        get_account_by_id,
    )


def calculate_health_score(account_id: str) -> tuple[int, list[str]]:
    """
    Calculate health score for an account.

    Returns:
        tuple: (score, reasons)
        - score: 0-100 (100 = healthy, 0 = critical)
        - reasons: list of strings explaining deductions
    """
    score = 100
    reasons = []

    # Get account info for downgrade flag
    account = get_account_by_id(account_id)
    if not account:
        return score, reasons

    # 1. Usage drop (last 30d vs previous 30d): -30 if dropped > 30%
    trend = get_usage_trend(account_id)
    if trend["change_pct"] < -30:
        score -= 30
        reasons.append(f"Usage dropped {abs(trend['change_pct']):.0f}% in last 30 days")

    # 2. Support ticket stats
    stats = get_ticket_stats(account_id, days=30)

    # Ticket count increase: -20 if more than 2 tickets
    if stats["count"] > 2:
        score -= 20
        reasons.append(f"{stats['count']} support tickets in last 30 days")

    # 3. Escalation flag: -15 if any
    if stats["escalations"] > 0:
        score -= 15
        reasons.append(f"{stats['escalations']} tickets escalated")

    # 4. Downgrade flag: -20
    if account.get("downgrade_flag") == "True":
        score -= 20
        reasons.append("Account has downgrade flag")

    # 5. Payment overdue: -20 if > 7 days, -35 if > 30 days
    days_overdue = account.get("days_overdue")
    if days_overdue and days_overdue != "" and days_overdue != "0":
        try:
            days = int(days_overdue)
            if days > 30:
                score -= 35
                reasons.append(f"Payment {days} days overdue (critical)")
            elif days > 7:
                score -= 20
                reasons.append(f"Payment {days} days overdue")
        except (ValueError, TypeError):
            pass

    # 6. Satisfaction score < 3: -15
    if stats["min_satisfaction"] is not None and stats["min_satisfaction"] < 3:
        score -= 15
        reasons.append(f"Satisfaction score: {stats['min_satisfaction']}/5")

    return max(0, score), reasons


def get_risk_level(health_score: int) -> str:
    """
    Convert health score to risk level.

    - < 40: high risk (red)
    - 40-70: medium risk (yellow)
    - > 70: low risk (green)
    """
    if health_score < 40:
        return "high"
    elif health_score <= 70:
        return "medium"
    else:
        return "low"


def get_autonomy_level(health_score: int, arr_amount: float) -> tuple[str, str]:
    """
    Determine if AI should act autonomously or ask for approval.

    Logic:
    - ALL accounts require human approval before taking action
    - The AI analyzes and recommends, but humans decide

    Returns:
        tuple: (level, reason)
        - level: always "needs_approval"
        - reason: explanation for the decision
    """
    arr = float(arr_amount) if arr_amount else 0

    # All accounts require approval - human-in-the-loop for all decisions
    if health_score < 40:
        return (
            "needs_approval",
            f"High-risk account (score {health_score}) requires human review before action"
        )
    else:
        return (
            "needs_approval",
            f"Account flagged for review — awaiting human approval"
        )


def get_at_risk_accounts(accounts: list[dict], threshold: int = 70) -> list[dict]:
    """
    Filter and enrich accounts that are at risk.

    Args:
        accounts: list of account dicts from database
        threshold: health score threshold (below = at risk)

    Returns:
        list of accounts with health_score, risk_level, autonomy_level added
    """
    at_risk = []

    for account in accounts:
        score, reasons = calculate_health_score(account["account_id"])

        if score <= threshold:
            arr = float(account.get("arr_amount") or 0)
            autonomy, autonomy_reason = get_autonomy_level(score, arr)

            enriched = {
                **account,
                "health_score": score,
                "risk_level": get_risk_level(score),
                "risk_reasons": reasons,
                "autonomy_level": autonomy,
                "autonomy_reason": autonomy_reason,
            }
            at_risk.append(enriched)

    # Sort by health score (worst first)
    at_risk.sort(key=lambda x: x["health_score"])

    return at_risk
