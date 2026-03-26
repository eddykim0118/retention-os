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

import anthropic


# Initialize Anthropic client
# It automatically reads ANTHROPIC_API_KEY from environment
client = anthropic.Anthropic()

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
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250514",
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

    except anthropic.APIError as e:
        print(f"[AGENT] API error: {e}")
        return None
    except Exception as e:
        print(f"[AGENT] Unexpected error: {e}")
        return None


def build_account_signals(account: dict, health_score: int, risk_reasons: list[str]) -> dict:
    """
    Build the signals dict to send to Claude.

    This combines account info with calculated health metrics.
    """
    # Import here to avoid circular imports
    try:
        from database import get_usage_trend, get_ticket_stats
    except ImportError:
        from backend.database import get_usage_trend, get_ticket_stats

    account_id = account["account_id"]

    # Get usage trend
    usage = get_usage_trend(account_id)

    # Get ticket stats
    tickets = get_ticket_stats(account_id)

    return {
        "account_name": account.get("account_name"),
        "industry": account.get("industry"),
        "plan_tier": account.get("plan_tier"),
        "seats": account.get("seats"),
        "mrr_amount": account.get("mrr_amount"),
        "arr_amount": account.get("arr_amount"),
        "health_score": health_score,
        "risk_reasons": risk_reasons,
        "usage_trend": {
            "recent_30d": usage["recent"],
            "previous_30d": usage["previous"],
            "change_percent": usage["change_pct"]
        },
        "ticket_stats": {
            "count_last_30d": tickets["count"],
            "escalations": tickets["escalations"],
            "min_satisfaction_score": tickets["min_satisfaction"]
        }
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
    arr = account_signals.get("arr_amount", 0)

    # Determine action based on signals
    if account_signals.get("ticket_stats", {}).get("escalations", 0) > 0:
        action = "support_escalation"
        reasoning = "Multiple escalated tickets indicate urgent support issues"
    elif account_signals.get("usage_trend", {}).get("change_percent", 0) < -30:
        action = "training_call"
        reasoning = "Significant usage drop suggests product friction"
    elif arr and float(arr) > 50000:
        action = "senior_outreach"
        reasoning = "High-value enterprise account needs executive attention"
    else:
        action = "training_call"
        reasoning = "General health decline warrants proactive outreach"

    return {
        "churn_risk_score": 100 - health_score,
        "risk_reasons": account_signals.get("risk_reasons", ["Health score declining"]),
        "next_best_action": action,
        "action_reasoning": reasoning,
        "why_not_others": "Other actions don't address the primary risk signal.",
        "generated_email": f"Subject: We want to help — {account_name}\n\nDear {account_name} team,\n\nWe noticed some changes in your usage and wanted to reach out...",
        "internal_memo": f"PRIORITY: {'HIGH' if health_score < 40 else 'MEDIUM'}\nAccount: {account_name}\nAction: {action}\nDeadline: 48 hours",
        "slack_message": f"🚨 *{account_name}* at risk (score: {health_score}) — Recommended: {action}",
        "urgency_deadline": "Action needed within 48 hours" if health_score < 40 else "Review within 1 week"
    }
