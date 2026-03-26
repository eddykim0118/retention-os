"""
Test script for email_service — Claude writes the email, Resend sends it.
Sends to TEST_EMAIL (songjisu2487@gmail.com) from .env.

Usage:
  python test_email.py
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_service import send_retention_email

TEST_EMAIL = os.getenv("TEST_EMAIL", "songjisu2487@gmail.com")

SCENARIOS = [
    {
        "account_name": "Vertex Systems",
        "contact_email": TEST_EMAIL,
        "health_score": 52,
        "risk_reason": "Invoice overdue by 14 days, no payment received",
        "arr": 18000,
        "ai_summary": "Vertex has a 14-day overdue invoice. Usage is healthy but financial risk is elevated.",
        "suggested_action": "Send invoice reminder and offer a short payment extension if needed.",
    },
    {
        "account_name": "Nimbus Analytics",
        "contact_email": TEST_EMAIL,
        "health_score": 28,
        "risk_reason": "Feature usage dropped 60% — dashboard crash, export broken for 3 weeks",
        "arr": 36000,
        "ai_summary": "4 unresolved support tickets, critical product friction. Usage down 60%.",
        "suggested_action": "Apologise for the disruption, share fix ETA, offer dedicated support.",
    },
    {
        "account_name": "Orion Global",
        "contact_email": TEST_EMAIL,
        "health_score": 35,
        "risk_reason": "Competitor mentions in tickets — team is evaluating alternative platforms",
        "arr": 102000,
        "ai_summary": "Orion ($102K ARR) is actively evaluating competitors. Two tickets reference alternatives.",
        "suggested_action": "Schedule executive call within 48h. Offer 20% discount + dedicated CSM.",
    },
]


async def main():
    resend_key = os.getenv("RESEND_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    print("=" * 60)
    print("Email Service Test — Claude + Resend")
    print(f"Sending to  : {TEST_EMAIL}")
    print(f"Claude      : {'✅ ready' if anthropic_key else '❌ ANTHROPIC_API_KEY missing'}")
    print(f"Resend      : {'✅ ready' if resend_key else '❌ RESEND_API_KEY missing — dry run only'}")
    print("=" * 60)

    if not anthropic_key:
        print("\n❌ ANTHROPIC_API_KEY not set. Cannot run test.")
        return

    for s in SCENARIOS:
        print(f"\n{'─' * 55}")
        print(f"▶ {s['account_name']} | ARR: ${s['arr']:,} | Health: {s['health_score']}/100")
        print(f"  Risk: {s['risk_reason']}")

        result = await send_retention_email(**s)

        if result.get("success") and result.get("should_send"):
            print(f"  ✅ Sent [{result['email_type']}] → {TEST_EMAIL}")
            print(f"  Subject : {result.get('subject', '')}")
            print(f"  Email ID: {result.get('email_id', '')}")
        elif result.get("should_send") is False:
            print(f"  ⏭️  Claude decided no email needed: {result.get('reason', '')}")
        else:
            print(f"  ❌ Failed [{result.get('email_type', '?')}]: {result.get('reason', '')}")

        print(f"  Reason  : {result.get('reason', '')}")

    print("\n" + "=" * 60)
    print(f"Done! Check inbox: {TEST_EMAIL} (also check spam folder)")


if __name__ == "__main__":
    asyncio.run(main())
