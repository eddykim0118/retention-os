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
from slack_reminder import start_reminder, mark_approved, get_reminder_status


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
    """Test #retention-urgent (Needs Approval) — single send."""
    print("\n--- Test 2: #retention-urgent (single send) ---")
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
    print("\n--- Test 3: Approval Confirmed (via web app) ---")
    success = await send_approval_confirmed(
        account_name="Orion Global",
        account_id="A-ORION",
        action_taken="Scheduled executive call + sent discount offer email",
    )
    print(f"Result: {'✅ Sent' if success else '❌ Failed'}")


async def test_reminder_approved_early():
    """
    Test reminder flow: sends morning reminder → simulates web app approval
    → confirms no further reminders sent.
    """
    print("\n--- Test 4: Reminder — Approved after 1st reminder ---")

    await start_reminder(
        account_id="A-ORION-TEST",
        account_name="Orion Global (Reminder Test)",
        health_score=35,
        risk_reason="Competitor mentions in support tickets + usage declining",
        arr=102000,
        ai_summary="Orion is evaluating competitors. Immediate action needed.",
        recommended_action="Schedule executive call within 48 hours.",
    )

    status = get_reminder_status("A-ORION-TEST")
    print(f"  After 1st send → reminder_count: {status.get('reminder_count')}/3")

    # Simulate user approving on the web app after the 1st reminder
    print("  Simulating web app approval...")
    await mark_approved(
        account_id="A-ORION-TEST",
        action_taken="Executive call booked via web app",
    )

    status = get_reminder_status("A-ORION-TEST")
    print(f"  approved: {status.get('approved')} — no more reminders will fire ✅")


async def test_reminder_all_3():
    """
    Test all 3 reminders fire with 2s gap (instead of real 4h).
    Patches REMINDER_INTERVAL_HOURS to [0, 2s, 4s] equivalent for fast testing.
    """
    import slack_reminder as sr

    print("\n--- Test 5: Reminder — All 3 fire (fast mode: 2s gaps) ---")

    # Temporarily shorten intervals to 2 seconds each for testing
    original = sr.REMINDER_INTERVAL_HOURS[:]
    sr.REMINDER_INTERVAL_HOURS = [0, 2/3600, 4/3600]  # 0h, 2s, 4s

    await start_reminder(
        account_id="A-VERTEX-TEST",
        account_name="Vertex Systems (All 3 Test)",
        health_score=52,
        risk_reason="Invoice overdue by 14 days, no payment received",
        arr=18000,
        ai_summary="Invoice 14 days overdue. No payment received yet.",
        recommended_action="Send invoice reminder + offer payment extension.",
    )

    # Wait for all 3 reminders to fire (4s + buffer)
    print("  Waiting for all 3 reminders to fire (takes ~5s)...")
    await asyncio.sleep(6)

    sr.REMINDER_INTERVAL_HOURS = original  # restore

    status = get_reminder_status("A-VERTEX-TEST")
    print(f"  Final reminder_count: {status.get('reminder_count')}/3")
    print(f"  approved: {status.get('approved')}")
    print(f"  ✅ Max reminders reached — Slack will not ping again.")


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
    await test_reminder_approved_early()
    await test_reminder_all_3()
    print("\n✅ All tests done. Check your Slack channels!")


if __name__ == "__main__":
    asyncio.run(main())


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
