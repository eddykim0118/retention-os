"""
fix_demo_data.py - Fix demo account data to achieve expected health scores

Issues found:
1. Nimbus usage date 2024-12-05 falls in "recent" period, diluting the drop
2. Orion only has 2 tickets (threshold is >2 for -20 deduction)

Expected scores after fix:
- Nimbus: ~35 (usage drop + tickets + escalations + low satisfaction)
- Vertex: ~65 (days_overdue - need to add this to health_score.py separately)
- Orion: ~20 (tickets + escalations + low satisfaction) → triggers needs_approval

Run from project root: python scripts/fix_demo_data.py
"""

import csv
from pathlib import Path

DB_DIR = Path(__file__).parent.parent / "backend" / "db"


def fix_nimbus_usage_date():
    """Fix the Nimbus usage date from 2024-12-05 to 2024-12-01"""
    csv_path = DB_DIR / "ravenstack_feature_usage.csv"

    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    # Find and fix the U-NIM004 row (the one with 2024-12-05)
    fixed = False
    for row in data:
        if row[0] == "U-NIM004" and row[2] == "2024-12-05":
            row[2] = "2024-12-01"  # Move to previous period
            fixed = True
            print(f"✓ Fixed U-NIM004 date: 2024-12-05 → 2024-12-01")
            break

    if not fixed:
        print("⚠️ U-NIM004 with date 2024-12-05 not found")
        return

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✓ Updated {csv_path.name}")


def set_orion_downgrade_flag():
    """Set downgrade_flag=True for Orion subscription to trigger -20 deduction"""
    csv_path = DB_DIR / "ravenstack_subscriptions.csv"

    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    # Find the downgrade_flag column index
    try:
        downgrade_idx = header.index("downgrade_flag")
    except ValueError:
        print("⚠️ downgrade_flag column not found")
        return

    # Find and update S-ORION
    fixed = False
    for row in data:
        if row[0] == "S-ORION":
            row[downgrade_idx] = "True"
            fixed = True
            print(f"✓ Set downgrade_flag=True for S-ORION")
            break

    if not fixed:
        print("⚠️ S-ORION subscription not found")
        return

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✓ Updated {csv_path.name}")


def add_orion_ticket():
    """Add a 3rd ticket for Orion to trigger >2 threshold"""
    csv_path = DB_DIR / "ravenstack_support_tickets.csv"

    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    # Check if we already have 3 Orion tickets
    orion_count = sum(1 for row in data if row[1] == "A-ORION")
    if orion_count >= 3:
        print(f"⚠️ Orion already has {orion_count} tickets, skipping")
        return

    # Add a 3rd ticket for Orion
    # Format: ticket_id, account_id, submitted_at, resolved_at, resolution_hours, priority, response_time_mins, satisfaction_score, escalation_flag, notes
    new_ticket = [
        "T-ORI003",
        "A-ORION",
        "2024-12-20",  # Between the other two tickets
        "",  # Not resolved
        "0",
        "high",
        "90",
        "1.5",  # Low satisfaction
        "True",  # Escalated!
        "Missing features that competitors have. Evaluating other options."
    ]

    data.append(new_ticket)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✓ Added T-ORI003 ticket for Orion (escalated, low satisfaction)")
    print(f"✓ Orion now has {orion_count + 1} tickets")


def verify_demo_data():
    """Print relevant rows for verification"""
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)

    # Check Nimbus usage
    csv_path = DB_DIR / "ravenstack_feature_usage.csv"
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        nimbus_usage = [r for r in reader if r["subscription_id"] == "S-NIMBUS"]

    print("\n--- Nimbus Usage (should have 4 in previous period, 4 in recent) ---")
    print("Previous period (before Dec 2): dates should be Nov 20, 25, 30, Dec 1")
    print("Recent period (Dec 2+): dates should be Dec 15, 20, 25, Jan 1")
    for u in nimbus_usage:
        period = "PREVIOUS" if u["usage_date"] < "2024-12-02" else "RECENT"
        print(f"  {u['usage_id']}: {u['usage_date']} - {u['usage_count']} ({period})")

    # Calculate expected trend
    previous_total = sum(int(u["usage_count"]) for u in nimbus_usage if u["usage_date"] < "2024-12-02")
    recent_total = sum(int(u["usage_count"]) for u in nimbus_usage if u["usage_date"] >= "2024-12-02")
    if previous_total > 0:
        change_pct = ((recent_total - previous_total) / previous_total) * 100
    else:
        change_pct = 0
    print(f"\n  Previous total: {previous_total}")
    print(f"  Recent total: {recent_total}")
    print(f"  Change: {change_pct:.1f}% {'✓ TRIGGERS -30' if change_pct < -30 else '✗ NOT ENOUGH DROP'}")

    # Check Orion tickets
    csv_path = DB_DIR / "ravenstack_support_tickets.csv"
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        orion_tickets = [r for r in reader if r["account_id"] == "A-ORION"]

    print("\n--- Orion Tickets (need >2 for -20 deduction) ---")
    escalations = 0
    min_sat = None
    for t in orion_tickets:
        esc = "ESCALATED" if t["escalation_flag"] == "True" else ""
        sat = t.get("satisfaction_score", "")
        if sat and sat != "":
            sat_val = float(sat)
            if min_sat is None or sat_val < min_sat:
                min_sat = sat_val
        if t["escalation_flag"] == "True":
            escalations += 1
        print(f"  {t['ticket_id']}: {t['submitted_at']} - {t['priority']} {esc} (sat: {sat})")

    print(f"\n  Total tickets: {len(orion_tickets)} {'✓ TRIGGERS -20' if len(orion_tickets) > 2 else '✗ NEED >2'}")
    print(f"  Escalations: {escalations} {'✓ TRIGGERS -15' if escalations > 0 else ''}")
    print(f"  Min satisfaction: {min_sat} {'✓ TRIGGERS -15' if min_sat and min_sat < 3 else ''}")

    # Check Orion downgrade flag
    csv_path = DB_DIR / "ravenstack_subscriptions.csv"
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        orion_sub = next((r for r in reader if r["subscription_id"] == "S-ORION"), None)

    downgrade_flag = orion_sub and orion_sub.get("downgrade_flag") == "True"
    print(f"  Downgrade flag: {downgrade_flag} {'✓ TRIGGERS -20' if downgrade_flag else ''}")

    # Expected Orion score
    orion_score = 100
    if len(orion_tickets) > 2:
        orion_score -= 20
    if escalations > 0:
        orion_score -= 15
    if min_sat and min_sat < 3:
        orion_score -= 15
    if downgrade_flag:
        orion_score -= 20
    print(f"\n  Expected Orion score: {orion_score}")
    print(f"  ARR: $102,000 → {'NEEDS APPROVAL' if orion_score < 40 else 'auto'}")


def main():
    print("Fixing demo data issues...\n")

    fix_nimbus_usage_date()
    add_orion_ticket()
    set_orion_downgrade_flag()
    verify_demo_data()

    print("\n" + "="*60)
    print("✅ Demo data fixes complete!")
    print("="*60)
    print("\nNext step: Add days_overdue check to health_score.py for Vertex")


if __name__ == "__main__":
    main()
