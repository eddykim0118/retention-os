"""
Test script for Slack webhook integration.
Run this after setting up your Slack workspace & webhooks.

Usage:
  export SLACK_ALERTS_WEBHOOK=https://hooks.slack.com/services/xxx/yyy/zzz
  export SLACK_URGENT_WEBHOOK=https://hooks.slack.com/services/xxx/yyy/zzz
  python test_slack.py
"""

import asyncio
import os
import sys

# Add parent directory to path so we can import slack_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slack_service import send_slack_alert, send_slack_urgent, send_approval_confirmed


async def test_alerts_channel():
    """Test #retention-alerts with a Nimbus-style low-health account."""
    print("\n--- Test 1: #retention-alerts (Auto-handled) ---")
    success = await send_slack_alert(
        account_name="Nimbus Analytics",
        account_id="A-NIMBUS",
        health_score=28,
        risk_reason="Feature usage dropped 60% in 3 weeks + 4 unresolved support tickets",
        arr=36000,
        ai_summary=(
            "Nimbus Analytics shows critical churn signals: dashboard crash reports, "
            "export feature broken for 3 weeks, and usage has fallen sharply. "
            "Immediate outreach recommended before renewal."
        ),
    )
    print(f"Result: {'✅ Sent' if success else '❌ Failed'}")


async def test_urgent_channel():
    """Test #retention-urgent with an Orion-style high-value account."""
    print("\n--- Test 2: #retention-urgent (Needs Approval) ---")
    success = await send_slack_urgent(
        account_name="Orion Global",
        account_id="A-ORION",
        health_score=35,
        risk_reason="Competitor mentions in support tickets + usage declining",
        arr=102000,
        ai_summary=(
            "Orion Global ($102K ARR) is actively evaluating competitor platforms. "
            "Two recent tickets mention alternatives. Usage down 28% over 6 weeks. "
            "This account is at high risk of churning within 30 days."
        ),
        recommended_action=(
            "Schedule executive call within 48 hours. "
            "Offer 3-month discount + dedicated CSM support."
        ),
    )
    print(f"Result: {'✅ Sent' if success else '❌ Failed'}")


async def test_approval_confirmed():
    """Test approval confirmation message."""
    print("\n--- Test 3: Approval Confirmed ---")
    success = await send_approval_confirmed(
        account_name="Orion Global",
        account_id="A-ORION",
        action_taken="Scheduled executive call + sent discount offer email",
    )
    print(f"Result: {'✅ Sent' if success else '❌ Failed'}")


async def main():
    alerts_webhook = os.getenv("SLACK_ALERTS_WEBHOOK")
    urgent_webhook = os.getenv("SLACK_URGENT_WEBHOOK")

    if not alerts_webhook or not urgent_webhook:
        print("⚠️  Webhook URLs not set! Please run:")
        print("  export SLACK_ALERTS_WEBHOOK=https://hooks.slack.com/services/...")
        print("  export SLACK_URGENT_WEBHOOK=https://hooks.slack.com/services/...")
        return

    print("🚀 Running Slack integration tests...")
    await test_alerts_channel()
    await test_urgent_channel()
    await test_approval_confirmed()
    print("\n✅ All tests done. Check your Slack channels!")


if __name__ == "__main__":
    asyncio.run(main())
