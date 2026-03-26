"""
Slack Notification Service for Retention OS
Sends alerts to #retention-alerts and #retention-urgent channels.

Slack is for NOTIFICATION only.
All approvals happen on the web app — Slack includes a direct link button.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# Webhook URLs from environment variables
SLACK_ALERTS_WEBHOOK = os.getenv("SLACK_ALERTS_WEBHOOK", "")
SLACK_URGENT_WEBHOOK = os.getenv("SLACK_URGENT_WEBHOOK", "")

# Base URL of the web app (frontend)
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")


def _account_url(account_id: str) -> str:
    return f"{APP_BASE_URL}/account/{account_id}"


# Keywords → department mapping
_DEPARTMENT_RULES = [
    (["invoice", "overdue", "payment", "billing", "refund", "charge", "pricing", "discount"], "💰 Finance"),
    (["bug", "crash", "error", "broken", "outage", "degraded", "slow", "timeout", "api",
      "feature", "export", "dashboard", "performance"], "🛠️ Engineering"),
    (["competitor", "alternative", "evaluating", "switching", "churn", "cancel"], "🤝 Sales"),
    (["onboarding", "training", "workflow", "setup", "adoption", "usage"], "🎓 Customer Success"),
]


def _infer_department(risk_reason: str) -> str:
    lower = risk_reason.lower()
    for keywords, department in _DEPARTMENT_RULES:
        if any(kw in lower for kw in keywords):
            return department
    return "📋 General"


async def send_slack_alert(
    account_name: str,
    account_id: str,
    health_score: int,
    risk_reason: str,
    arr: int,
    ai_summary: str,
) -> bool:
    """
    Send a churn risk alert to #retention-alerts channel.
    Auto-handled accounts (ARR < $50K) — no approval needed.
    Includes a link to view the account on the web app.
    """
    account_url = _account_url(account_id)
    department = _infer_department(risk_reason)

    message = {
        "text": f":warning: *Churn Risk Detected: {account_name}*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚠️ Churn Risk: {account_name}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Account ID:*\n{account_id}"},
                    {"type": "mrkdwn", "text": f"*Health Score:*\n{health_score}/100"},
                    {"type": "mrkdwn", "text": f"*ARR:*\n${arr:,}"},
                    {"type": "mrkdwn", "text": f"*Department:*\n{department}"},
                    {"type": "mrkdwn", "text": f"*Risk Reason:*\n{risk_reason}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Analysis:*\n{ai_summary}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"👤 <{account_url}|View Account>",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "✅ Auto-handled by Retention OS | #retention-alerts",
                    }
                ],
            },
        ],
    }

    return await _post_to_slack(SLACK_ALERTS_WEBHOOK, message)


async def send_slack_urgent(
    account_name: str,
    account_id: str,
    health_score: int,
    risk_reason: str,
    arr: int,
    ai_summary: str,
    recommended_action: str,
) -> bool:
    """
    Send an urgent notification to #retention-urgent channel.
    High-value accounts (ARR >= $50K) — approval happens on the web app.
    Slack includes a direct 'Approve on Web App' button link.
    """
    account_url = _account_url(account_id)
    department = _infer_department(risk_reason)

    message = {
        "text": f":rotating_light: *URGENT — Action Required: {account_name}*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 URGENT — Action Required: {account_name}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Account ID:*\n{account_id}"},
                    {"type": "mrkdwn", "text": f"*Health Score:*\n{health_score}/100"},
                    {"type": "mrkdwn", "text": f"*ARR:*\n${arr:,} 🔴 High Value"},
                    {"type": "mrkdwn", "text": f"*Department:*\n{department}"},
                    {"type": "mrkdwn", "text": f"*Risk Reason:*\n{risk_reason}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Analysis:*\n{ai_summary}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recommended Action:*\n{recommended_action}",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ <{account_url}|Approve on Web App>",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🔴 Approval required on web app | #retention-urgent",
                    }
                ],
            },
        ],
    }

    return await _post_to_slack(SLACK_URGENT_WEBHOOK, message)


async def _post_to_slack(webhook_url: str, payload: dict) -> bool:
    """
    Internal helper — POST payload to the given Slack webhook URL.
    Returns True on success, False on failure.
    """
    if not webhook_url:
        print("[Slack] WARNING: Webhook URL not set. Skipping.")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=5.0,
            )
            if response.status_code == 200 and response.text == "ok":
                print(f"[Slack] ✅ Message sent successfully.")
                return True
            else:
                print(f"[Slack] ❌ Failed: {response.status_code} — {response.text}")
                return False
    except Exception as e:
        print(f"[Slack] ❌ Exception: {e}")
        return False
