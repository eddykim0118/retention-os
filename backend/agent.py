"""
agent.py - Claude API integration for account analysis

This is the "brain" of the AI employee. It uses Claude to:
1. Analyze customer signals (usage, tickets, etc.)
2. Decide what action to take
3. Generate customer-facing email and internal memo
4. Produce a ready-to-send Slack message

Key technique: tool_use
Instead of asking Claude to return JSON (which can vary), we define a "tool"
that Claude must call. This forces Claude to return structured data in our exact schema.
"""

import json
import os
from typing import Optional

try:
    import anthropic
except ImportError:
    anthropic = None


# Initialize Anthropic client
# It automatically reads ANTHROPIC_API_KEY from environment
client = anthropic.Anthropic() if anthropic else None

# Define the tool that Claude must use to submit its analysis
ANALYSIS_TOOL = {
    "name": "submit_analysis",
    "description": "Submit the churn risk analysis and recommended action for an account. You MUST use this tool to provide your analysis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "churn_risk_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Risk of churn from 0-100. Higher = more likely to churn."
            },
            "risk_reasons": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of specific reasons this account is at risk. Be concrete and data-driven."
            },
            "next_best_action": {
                "type": "string",
                "enum": ["training_call", "support_escalation", "finance_reminder", "senior_outreach"],
                "description": "The single best action to take. training_call=product friction, support_escalation=urgent tickets, finance_reminder=billing issues, senior_outreach=high-value at-risk"
            },
            "action_reasoning": {
                "type": "string",
                "description": "Why this action is the right choice. Be specific about what problem it solves."
            },
            "why_not_others": {
                "type": "string",
                "description": "Briefly explain why the other actions were NOT chosen."
            },
            "generated_email": {
                "type": "string",
                "description": "A ready-to-send email to the customer. Professional, empathetic, action-oriented."
            },
            "internal_memo": {
                "type": "string",
                "description": "Internal memo for the CS team. Include priority, account summary, recommended actions, deadline, and owner placeholder."
            },
            "slack_message": {
                "type": "string",
                "description": "A concise Slack message for the CS team. Format: emoji + account name + key risk + recommended action."
            },
            "urgency_deadline": {
                "type": "string",
                "description": "How urgent is this? e.g., 'Action needed within 24 hours' or 'Review within 1 week'"
            }
        },
        "required": [
            "churn_risk_score", "risk_reasons", "next_best_action",
            "action_reasoning", "why_not_others", "generated_email",
            "internal_memo", "slack_message", "urgency_deadline"
        ]
    }
}

SYSTEM_PROMPT = """You are an AI Account Manager employee at a B2B SaaS company. You are NOT an assistant — you are an employee who ACTS.

Your job:
1. Analyze customer health signals
2. Identify the root cause of risk
3. Decide the SINGLE best action to take
4. Prepare communications (email to customer, memo for team, Slack alert)

Available actions:
- training_call: For product friction — customer struggling to use the product
- support_escalation: For urgent unresolved tickets — customer frustrated with support
- finance_reminder: For billing issues — payment problems but otherwise happy customer
- senior_outreach: For high-value enterprise accounts showing multiple risk signals — needs executive attention

Guidelines:
- Be data-driven: cite specific numbers from the signals
- Be decisive: pick ONE action, not a combination
- Be specific: explain exactly why you chose this action and not others
- Be professional: the email will be sent to real customers
- Be concise: the Slack message should be scannable in 5 seconds

You MUST use the submit_analysis tool to provide your analysis. Do not respond with plain text."""


def analyze_account(account_signals: dict) -> Optional[dict]:
    """
    Use Claude to analyze an account and decide what action to take.

    Args:
        account_signals: Dict containing account info and health signals
            - account_name, industry, plan_tier, seats
            - mrr_amount, arr_amount
            - health_score, risk_reasons
            - usage_trend (recent vs previous)
            - ticket_stats (count, escalations, satisfaction)

    Returns:
        Dict with analysis results, or None if analysis failed
    """
    if client is None:
        print("[AGENT] Anthropic SDK not installed; skipping real API analysis")
        return None

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=[ANALYSIS_TOOL],
            tool_choice={"type": "tool", "name": "submit_analysis"},  # Force tool use
            messages=[{
                "role": "user",
                "content": f"Analyze this account and decide what action to take:\n\n{json.dumps(account_signals, indent=2)}"
            }]
        )

        # Extract the tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_analysis":
                return block.input

        # If we get here, Claude didn't use the tool (shouldn't happen with tool_choice)
        print("[AGENT] Warning: Claude did not use submit_analysis tool")
        return None

    except Exception as e:
        if anthropic and isinstance(e, anthropic.APIError):
            print(f"[AGENT] API error: {e}")
            return None
        print(f"[AGENT] Unexpected error: {e}")
        return None


def build_account_signals(account: dict, health_score: int, risk_reasons: list[str]) -> dict:
    """
    Build the signals dict to send to Claude.

    This combines account info with calculated health metrics.
    """
    # Import here to avoid circular imports
    try:
        from database import get_usage_trend, get_ticket_stats, get_account_tickets
    except ImportError:
        from backend.database import get_usage_trend, get_ticket_stats, get_account_tickets

    account_id = account["account_id"]

    # Get usage trend
    usage = get_usage_trend(account_id)

    # Get ticket stats
    tickets = get_ticket_stats(account_id)
    recent_tickets = get_account_tickets(account_id)
    unresolved_tickets = sum(1 for ticket in recent_tickets if not ticket.get("closed_at"))
    ticket_notes = [ticket.get("notes") for ticket in recent_tickets if ticket.get("notes")]
    competitor_mentions = sum(
        1
        for note in ticket_notes
        if any(keyword in note.lower() for keyword in ("competitor", "alternative", "evaluating"))
    )

    return {
        "account_name": account.get("account_name"),
        "industry": account.get("industry"),
        "plan_tier": account.get("plan_tier"),
        "seats": account.get("seats"),
        "mrr_amount": account.get("mrr_amount"),
        "arr_amount": account.get("arr_amount"),
        "days_overdue": account.get("days_overdue"),
        "health_score": health_score,
        "risk_reasons": risk_reasons,
        "usage_trend": {
            "recent_30d": usage["recent"],
            "previous_30d": usage["previous"],
            "change_percent": usage["change_pct"]
        },
        "ticket_stats": {
            "count_last_30d": tickets["count"],
            "unresolved": unresolved_tickets,
            "escalations": tickets["escalations"],
            "min_satisfaction_score": tickets["min_satisfaction"],
            "competitor_mentions": competitor_mentions,
            "ticket_notes": ticket_notes,
        },
    }


# =============================================================================
# MOCK FUNCTION FOR TESTING WITHOUT API
# =============================================================================

def mock_analyze_account(account_signals: dict) -> dict:
    """
    Mock analysis for testing without hitting the Claude API.

    Returns a realistic-looking analysis based on the signals.
    """
    account_name = account_signals.get("account_name", "Unknown Account")
    health_score = account_signals.get("health_score", 50)
    arr = float(account_signals.get("arr_amount") or 0)
    usage_drop = account_signals.get("usage_trend", {}).get("change_percent", 0)
    ticket_stats = account_signals.get("ticket_stats", {})
    ticket_count = ticket_stats.get("count_last_30d", 0) or 0
    unresolved_tickets = ticket_stats.get("unresolved", 0) or 0
    escalations = ticket_stats.get("escalations", 0) or 0
    min_satisfaction = ticket_stats.get("min_satisfaction_score")
    competitor_mentions = ticket_stats.get("competitor_mentions", 0) or 0

    try:
        days_overdue = int(account_signals.get("days_overdue") or 0)
    except (TypeError, ValueError):
        days_overdue = 0

    # Match the demo scenarios the frontend was designed around.
    if days_overdue > 7:
        action = "finance_reminder"
        reasoning = "The account remains active, and the clearest retention risk is the overdue invoice."
        risk_reasons = [
            f"Invoice is overdue by {days_overdue} days",
            "Usage is healthy, suggesting this is a payment issue instead of product friction",
            "No escalated support tickets",
        ]
        why_not_others = (
            "training_call: usage is steady. support_escalation: there is no active support backlog. "
            "senior_outreach: account value does not justify executive intervention."
        )
        urgency_deadline = "Resolve within 72 hours"
    elif health_score < 40 and arr >= 50000:
        action = "senior_outreach"
        reasoning = "This is a high-value account with multiple retention signals, so executive attention is the right next step."
        risk_reasons = []
        if competitor_mentions:
            risk_reasons.append("Recent support ticket mentions competitor evaluation")
        if min_satisfaction is not None and float(min_satisfaction) < 3:
            risk_reasons.append(f"Customer sentiment is {float(min_satisfaction):.0f}/5 across recent tickets")
        if unresolved_tickets > 0 or escalations > 0:
            risk_reasons.append("Critical workflow issues remain unresolved")
        risk_reasons.append("ARR exceeds the executive approval threshold")
        why_not_others = (
            "finance_reminder: no billing issue is present. training_call: adoption is not the primary risk. "
            "support_escalation alone is too narrow for a high-value account with competitive pressure."
        )
        urgency_deadline = "Executive response needed today"
    elif usage_drop < -30:
        action = "training_call"
        reasoning = "The sharp usage decline points to product friction, so a guided training call is the best recovery path."
        risk_reasons = [f"Usage dropped {abs(usage_drop):.0f}% in the last 30 days"]
        if unresolved_tickets:
            risk_reasons.append(f"{unresolved_tickets} unresolved support tickets")
        if escalations:
            risk_reasons.append(f"{escalations} tickets escalated")
        if min_satisfaction is not None and float(min_satisfaction) < 3:
            risk_reasons.append(f"Satisfaction score: {float(min_satisfaction):.0f}/5")
        why_not_others = (
            "finance_reminder: no billing issue detected. support_escalation alone would not address the adoption problem. "
            "senior_outreach: ARR is below the executive approval threshold."
        )
        urgency_deadline = "Action needed within 48 hours"
    elif escalations > 0 or unresolved_tickets > 2:
        action = "support_escalation"
        reasoning = "Open escalations are the dominant risk signal and need immediate support intervention."
        risk_reasons = [
            f"{ticket_count} support tickets in the last 30 days",
            f"{escalations} tickets escalated",
        ]
        if min_satisfaction is not None and float(min_satisfaction) < 3:
            risk_reasons.append(f"Satisfaction score: {float(min_satisfaction):.0f}/5")
        why_not_others = (
            "training_call: the primary issue is support resolution speed. finance_reminder: no billing issue detected. "
            "senior_outreach: executive involvement is not necessary yet."
        )
        urgency_deadline = "Escalate within 24 hours"
    else:
        action = "training_call"
        reasoning = "A proactive training touchpoint is the best way to reinforce adoption before risk increases."
        risk_reasons = account_signals.get("risk_reasons", ["Health score declining"])
        why_not_others = "No stronger billing, support, or executive risk signal is present."
        urgency_deadline = "Review within 1 week"

    priority = "CRITICAL" if health_score < 30 else "HIGH" if health_score < 40 else "MEDIUM"
    action_label = action.replace("_", " ").title()

    return {
        "churn_risk_score": 100 - health_score,
        "risk_reasons": risk_reasons,
        "next_best_action": action,
        "action_reasoning": reasoning,
        "why_not_others": why_not_others,
        "generated_email": (
            f"Subject: Support for {account_name}\n\n"
            f"Hi {account_name} team,\n\n"
            f"We identified a risk signal on your account and want to help quickly. "
            f"Our recommended next step is a {action_label.lower()} to address the issue directly.\n\n"
            "Reply with the best contact and timing, and we will coordinate immediately.\n\n"
            "Best,\nCustomer Success"
        ),
        "internal_memo": (
            f"PRIORITY: {priority}\n"
            f"Account: {account_name}\n"
            f"Health Score: {health_score}\n"
            f"Recommended Action: {action_label}\n"
            f"Risk Signals: {'; '.join(risk_reasons)}\n"
            f"Deadline: {urgency_deadline}"
        ),
        "slack_message": f"🚨 {account_name} is at risk (score: {health_score}) — recommended action: {action_label}",
        "urgency_deadline": urgency_deadline,
    }
