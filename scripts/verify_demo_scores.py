"""
verify_demo_scores.py - Verify health scores for demo accounts

Expected results:
- Nimbus Analytics: ~35 (usage drop + tickets + escalations + low satisfaction)
- Vertex Systems: ~80 (days_overdue=14 → -20)
- Orion Global: ~30 (tickets + escalations + low satisfaction + downgrade) → NEEDS APPROVAL

Run from project root: python scripts/verify_demo_scores.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from database import init_database, get_account_by_id, get_usage_trend, get_ticket_stats
from health_score import calculate_health_score, get_risk_level, get_autonomy_level


def verify_account(account_id: str, account_name: str, expected_autonomy: str):
    """Verify health score and autonomy for a demo account"""
    print(f"\n{'='*60}")
    print(f"{account_name} ({account_id})")
    print("="*60)

    account = get_account_by_id(account_id)
    if not account:
        print(f"❌ Account not found!")
        return

    # Get components
    usage_trend = get_usage_trend(account_id)
    ticket_stats = get_ticket_stats(account_id, days=30)

    # Calculate health score
    health_score, reasons = calculate_health_score(account_id)
    risk_level = get_risk_level(health_score)

    # Get autonomy
    arr = float(account.get("arr_amount") or 0)
    autonomy, autonomy_reason = get_autonomy_level(health_score, arr)

    # Print results
    print(f"\nHealth Score: {health_score}/100 ({risk_level} risk)")
    print(f"ARR: ${arr:,.0f}")
    print(f"Autonomy: {autonomy}")

    print(f"\n--- Risk Signals ---")
    for reason in reasons:
        print(f"  • {reason}")

    if not reasons:
        print("  (none)")

    print(f"\n--- Raw Data ---")
    print(f"  Usage trend: {usage_trend}")
    print(f"  Ticket stats: {ticket_stats}")
    print(f"  Downgrade flag: {account.get('downgrade_flag')}")
    print(f"  Days overdue: {account.get('days_overdue')}")

    # Verify autonomy
    if autonomy == expected_autonomy:
        print(f"\n✅ Autonomy matches expected: {autonomy}")
    else:
        print(f"\n❌ Autonomy mismatch! Expected: {expected_autonomy}, Got: {autonomy}")

    return health_score, autonomy


def main():
    print("Initializing database...")
    init_database()

    print("\n" + "="*60)
    print("DEMO ACCOUNT VERIFICATION")
    print("="*60)

    results = []

    # Nimbus: high-risk but low ARR → auto
    score, autonomy = verify_account("A-NIMBUS", "Nimbus Analytics", "auto")
    results.append(("Nimbus", score, autonomy, "auto"))

    # Vertex: payment overdue → medium risk, auto
    score, autonomy = verify_account("A-VERTEX", "Vertex Systems", "auto")
    results.append(("Vertex", score, autonomy, "auto"))

    # Orion: high-risk AND high ARR → needs_approval
    score, autonomy = verify_account("A-ORION", "Orion Global", "needs_approval")
    results.append(("Orion", score, autonomy, "needs_approval"))

    # Summary table
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Account':<20} {'Score':<10} {'Autonomy':<18} {'Expected':<18} {'Match'}")
    print("-"*60)
    for name, score, actual, expected in results:
        match = "✅" if actual == expected else "❌"
        print(f"{name:<20} {score:<10} {actual:<18} {expected:<18} {match}")


if __name__ == "__main__":
    main()
