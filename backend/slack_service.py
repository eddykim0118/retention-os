"""
Slack Notification Service for Retention OS
Sends alerts to #retention-alerts and #retention-urgent channels
"""

import os
import httpx
from typing import Optional


# Webhook URLs from environment variables
SLACK_ALERTS_WEBHOOK = os.getenv("SLACK_ALERTS_WEBHOOK", "")
SLACK_URGENT_WEBHOOK = os.getenv("SLACK_URGENT_WEBHOOK", "")


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
    Used for accounts that are auto-handled (ARR < $50K).
    """
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
    Send an urgent approval request to #retention-urgent channel.
    Used for high-value accounts (ARR >= $50K) that need human approval.
    """
    message = {
        "text": f":rotating_light: *URGENT — Approval Needed: {account_name}*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 URGENT — Approval Needed: {account_name}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Account ID:*\n{account_id}"},
                    {"type": "mrkdwn", "text": f"*Health Score:*\n{health_score}/100"},
                    {"type": "mrkdwn", "text": f"*ARR:*\n${arr:,} 🔴 High Value"},
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
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🔴 Waiting for human approval | #retention-urgent",
                    }
                ],
            },
        ],
    }

    return await _post_to_slack(SLACK_URGENT_WEBHOOK, message)


async def send_approval_confirmed(
    account_name: str,
    account_id: str,
    action_taken: str,
) -> bool:
    """
    Notify #retention-urgent that an action was approved and executed.
    """
    message = {
        "text": f":white_check_mark: Approved & Executed: {account_name}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Approved & Executed*: {account_name} (`{account_id}`)\n*Action:* {action_taken}",
                },
            }
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
