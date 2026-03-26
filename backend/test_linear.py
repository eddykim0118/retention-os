"""
Test script for Linear ticket creation (dry-run if no API key set).
Run:
  export LINEAR_API_KEY=lin_api_...
  export LINEAR_TEAM_ID=your-team-id
  python test_linear.py
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linear_service import create_linear_ticket, _infer_department, _build_ticket

# ── 3 demo accounts from the hackathon dataset ───────────────────────────────

SCENARIOS = [
    {
        "account_name": "Vertex Systems",
        "account_id": "A-VERTEX",
        "health_score": 52,
        "risk_reason": "Invoice overdue by 14 days, no payment received",
        "arr": 18000,
        "ai_summary": (
            "Vertex Systems has an outstanding invoice 14 days overdue. "
            "Usage remains healthy but financial risk is elevated. "
            "Immediate billing outreach recommended."
        ),
    },
    {
        "account_name": "Nimbus Analytics",
        "account_id": "A-NIMBUS",
        "health_score": 28,
        "risk_reason": "Feature usage dropped 60% — dashboard crash, export broken for 3 weeks",
        "arr": 36000,
        "ai_summary": (
            "Nimbus Analytics shows critical product friction: 4 unresolved tickets, "
            "dashboard crashes, and export feature broken. Usage down 60%. "
            "Engineering fix needed urgently."
        ),
    },
    {
        "account_name": "Orion Global",
        "account_id": "A-ORION",
        "health_score": 35,
        "risk_reason": "Competitor mentions in tickets — team is evaluating alternative platforms",
        "arr": 102000,
        "ai_summary": (
            "Orion Global ($102K ARR) is actively evaluating competitors. "
            "Two support tickets reference alternative platforms. "
            "Executive-level intervention required."
        ),
    },
]


async def dry_run():
    """Preview title + description without calling Linear API."""
    print("\n" + "=" * 60)
    print("DRY RUN — No API key needed")
    print("=" * 60)

    for s in SCENARIOS:
        dept, emoji, priority = _infer_department(s["risk_reason"])
        title, description = _build_ticket(
            s["account_name"], s["account_id"], s["health_score"],
            s["risk_reason"], s["arr"], s["ai_summary"], dept, emoji,
        )
        print(f"\n{'─' * 55}")
        print(f"Department : {emoji} {dept}  (Linear priority: {priority})")
        print(f"Title      : {title}")
        print(f"\nDescription preview:\n{description[:300]}...")


async def live_run():
    """Actually create tickets in Linear."""
    print("\n" + "=" * 60)
    print("LIVE RUN — Creating Linear tickets")
    print("=" * 60)

    for s in SCENARIOS:
        result = await create_linear_ticket(**s)
        dept = result.get("department", "?")
        if result["success"]:
            print(f"\n✅ [{dept}] {result['title']}")
            print(f"   🔗 {result['issue_url']}")
        else:
            print(f"\n❌ [{dept}] Failed to create ticket for {s['account_name']}")


async def main():
    has_key = bool(os.getenv("LINEAR_API_KEY")) and bool(os.getenv("LINEAR_TEAM_ID"))

    # Always show dry run first
    await dry_run()

    if has_key:
        print("\n\nLinear credentials found — running live ticket creation...")
        await live_run()
    else:
        print("\n\n⚠️  LINEAR_API_KEY / LINEAR_TEAM_ID not set.")
        print("Set them to create real tickets:")
        print("  export LINEAR_API_KEY=lin_api_...")
        print("  export LINEAR_TEAM_ID=your-team-id")


if __name__ == "__main__":
    asyncio.run(main())
