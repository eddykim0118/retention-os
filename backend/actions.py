"""
actions.py - External actions (Slack, Linear, Email)

This is the "hands" of the AI employee — it actually DOES things:
- Sends Slack messages to alert the team
- Creates Linear tickets for follow-up
- Sends approved emails through Resend

Key design: Graceful fallback
If webhooks aren't configured, we log to console instead of crashing.
This lets you develop and test without external services set up.
"""

import os
from typing import Optional

import requests


# =============================================================================
# SLACK INTEGRATION
# =============================================================================

def send_slack_alert(channel_type: str, message: str) -> dict:
    """
    Send a message to Slack via webhook.

    Args:
        channel_type: "alerts" for routine alerts, "urgent" for high-priority
        message: The message text to send

    Returns:
        dict with "success" bool and "detail" string
    """
    # Get the appropriate webhook URL
    if channel_type == "urgent":
        webhook_url = os.environ.get("SLACK_URGENT_WEBHOOK")
        channel_name = "#retention-urgent"
    else:
        webhook_url = os.environ.get("SLACK_ALERTS_WEBHOOK")
        channel_name = "#retention-alerts"

    # If no webhook configured, mock it
    if not webhook_url:
        print(f"[MOCK SLACK] {channel_name}: {message}")
        return {
            "success": True,
            "mock": True,
            "detail": f"Mock sent to {channel_name}"
        }

    try:
        response = requests.post(
            webhook_url,
            json={"text": message},
            timeout=10
        )

        if response.status_code == 200:
            print(f"[SLACK] Sent to {channel_name}: {message[:50]}...")
            return {
                "success": True,
                "mock": False,
                "detail": f"Sent to {channel_name}"
            }
        else:
            print(f"[SLACK ERROR] Status {response.status_code}: {response.text}")
            return {
                "success": False,
                "mock": False,
                "detail": f"Slack API error: {response.status_code}"
            }

    except requests.RequestException as e:
        print(f"[SLACK ERROR] Request failed: {e}")
        return {
            "success": False,
            "mock": False,
            "detail": f"Request failed: {str(e)}"
        }


def format_slack_alert_message(
    account_name: str,
    health_score: int,
    action: str,
    reasoning: str,
    urgency: str
) -> str:
    """
    Format a nice Slack message for an at-risk account.

    Uses Slack's mrkdwn format for better readability.
    """
    # Risk emoji based on score
    if health_score < 40:
        emoji = "🚨"
        risk_label = "HIGH RISK"
    elif health_score < 70:
        emoji = "⚠️"
        risk_label = "MEDIUM RISK"
    else:
        emoji = "ℹ️"
        risk_label = "LOW RISK"

    # Action emoji
    action_emojis = {
        "training_call": "📞",
        "support_escalation": "🎫",
        "finance_reminder": "💰",
        "senior_outreach": "👔"
    }
    action_emoji = action_emojis.get(action, "📋")

    return f"""{emoji} *{risk_label}: {account_name}*
Health Score: {health_score}/100

{action_emoji} *Recommended Action:* {action.replace('_', ' ').title()}
{reasoning}

⏰ {urgency}"""


# =============================================================================
# LINEAR INTEGRATION (STRETCH GOAL)
# =============================================================================

def create_linear_ticket(
    title: str,
    description: str,
    priority: int = 2
) -> dict:
    """
    Create a ticket in Linear.

    Args:
        title: Ticket title
        description: Ticket description (markdown supported)
        priority: 1=urgent, 2=high, 3=medium, 4=low

    Returns:
        dict with "success" bool and ticket details if successful
    """
    api_key = os.environ.get("LINEAR_API_KEY")
    team_id = os.environ.get("LINEAR_TEAM_ID")

    # If not configured, mock it
    if not api_key or not team_id:
        print(f"[MOCK LINEAR] Would create ticket: {title}")
        return {
            "success": True,
            "mock": True,
            "detail": "Mock ticket created",
            "ticket_id": "MOCK-123",
            "ticket_url": "https://linear.app/mock/MOCK-123"
        }

    try:
        response = requests.post(
            "https://api.linear.app/graphql",
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json"
            },
            json={
                "query": """
                    mutation CreateIssue($input: IssueCreateInput!) {
                        issueCreate(input: $input) {
                            success
                            issue {
                                id
                                identifier
                                url
                            }
                        }
                    }
                """,
                "variables": {
                    "input": {
                        "teamId": team_id,
                        "title": title,
                        "description": description,
                        "priority": priority
                    }
                }
            },
            timeout=10
        )

        data = response.json()

        if data.get("data", {}).get("issueCreate", {}).get("success"):
            issue = data["data"]["issueCreate"]["issue"]
            print(f"[LINEAR] Created ticket: {issue['identifier']}")
            return {
                "success": True,
                "mock": False,
                "detail": f"Created {issue['identifier']}",
                "ticket_id": issue["identifier"],
                "ticket_url": issue["url"]
            }
        else:
            errors = data.get("errors", [])
            print(f"[LINEAR ERROR] {errors}")
            return {
                "success": False,
                "mock": False,
                "detail": f"Linear API error: {errors}"
            }

    except requests.RequestException as e:
        print(f"[LINEAR ERROR] Request failed: {e}")
        return {
            "success": False,
            "mock": False,
            "detail": f"Request failed: {str(e)}"
        }


def format_linear_ticket(
    account_name: str,
    health_score: int,
    action: str,
    reasoning: str,
    risk_reasons: list[str],
    urgency: str
) -> tuple[str, str]:
    """
    Format title and description for a Linear ticket.

    Returns:
        tuple: (title, description)
    """
    title = f"[Retention] {account_name} — {action.replace('_', ' ').title()}"

    description = f"""## Account Health Alert

**Account:** {account_name}
**Health Score:** {health_score}/100
**Recommended Action:** {action.replace('_', ' ').title()}

### Risk Signals
{chr(10).join(f"- {r}" for r in risk_reasons)}

### Reasoning
{reasoning}

### Urgency
{urgency}

---
*Auto-generated by Retention OS AI*
"""

    return title, description


# =============================================================================
# EMAIL INTEGRATION
# =============================================================================

def send_email(account_name: str, email_content: str, to_email: Optional[str] = None) -> dict:
    """
    Send an approved email through Resend.

    The dataset does not include customer contact emails, so TEST_EMAIL is used
    as the approval/demo recipient by default.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("RESEND_FROM_EMAIL")
    recipient = to_email or os.environ.get("TEST_EMAIL")

    if not api_key or not from_email or not recipient:
        print(f"[MOCK EMAIL] Would send email for {account_name} to {recipient or 'TEST_EMAIL'}")
        return {
            "success": True,
            "mock": True,
            "detail": f"Mock email prepared for {recipient or 'TEST_EMAIL'}",
            "recipient": recipient or "TEST_EMAIL",
        }

    subject, body = _split_email_content(email_content, account_name)

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_email,
                "to": [recipient],
                "subject": subject,
                "text": body,
            },
            timeout=10,
        )

        if response.status_code in (200, 201):
            data = response.json()
            print(f"[EMAIL] Sent email for {account_name} to {recipient}")
            return {
                "success": True,
                "mock": False,
                "detail": f"Sent email to {recipient}",
                "recipient": recipient,
                "email_id": data.get("id"),
            }

        print(f"[EMAIL ERROR] Status {response.status_code}: {response.text}")
        return {
            "success": False,
            "mock": False,
            "detail": f"Email API error: {response.status_code}",
            "recipient": recipient,
        }

    except requests.RequestException as e:
        print(f"[EMAIL ERROR] Request failed: {e}")
        return {
            "success": False,
            "mock": False,
            "detail": f"Request failed: {str(e)}",
            "recipient": recipient,
        }


def _split_email_content(email_content: str, account_name: str) -> tuple[str, str]:
    """Extract a subject/body pair from generated email content."""
    default_subject = f"Support for {account_name}"

    if not email_content:
        return default_subject, ""

    lines = email_content.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip() or default_subject
        body = "\n".join(lines[1:]).strip()
        return subject, body

    return default_subject, email_content.strip()
