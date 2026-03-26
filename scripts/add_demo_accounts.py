"""
add_demo_accounts.py - Add demo accounts to CSV files

This script safely modifies the RavenStack CSV files to add:
- 3 demo accounts (Nimbus, Vertex, Orion)
- New columns where needed (days_overdue, notes)
- Related subscriptions, tickets, and usage data

Run from project root: python scripts/add_demo_accounts.py
"""

import csv
from pathlib import Path

# Paths
DB_DIR = Path(__file__).parent.parent / "backend" / "db"

def add_demo_accounts():
    """Add 3 demo account rows to accounts.csv"""
    csv_path = DB_DIR / "ravenstack_accounts.csv"

    # Read existing data
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    # New demo accounts
    new_accounts = [
        ["A-NIMBUS", "Nimbus Analytics", "DevTools", "US", "2024-01-15", "organic", "Enterprise", "45", "False", "False"],
        ["A-VERTEX", "Vertex Systems", "FinTech", "US", "2024-03-01", "partner", "Pro", "12", "False", "False"],
        ["A-ORION", "Orion Global", "Cybersecurity", "US", "2023-06-10", "event", "Enterprise", "85", "False", "False"],
    ]

    # Append new accounts
    data.extend(new_accounts)

    # Write back
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✓ Added 3 accounts to {csv_path.name}")
    return csv_path


def add_subscriptions_with_overdue():
    """Add days_overdue column and 3 demo subscription rows"""
    csv_path = DB_DIR / "ravenstack_subscriptions.csv"

    # Read existing data
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    # Add days_overdue column to header
    header.append("days_overdue")

    # Add days_overdue=0 to all existing rows
    for row in data:
        row.append("0")

    # New demo subscriptions (with days_overdue at the end)
    new_subscriptions = [
        ["S-NIMBUS", "A-NIMBUS", "2024-01-15", "", "Enterprise", "45", "3000", "36000", "False", "False", "False", "False", "monthly", "True", "0"],
        ["S-VERTEX", "A-VERTEX", "2024-03-01", "", "Pro", "12", "1500", "18000", "False", "False", "False", "False", "monthly", "True", "14"],
        ["S-ORION", "A-ORION", "2023-06-10", "", "Enterprise", "85", "8500", "102000", "False", "False", "False", "False", "annual", "True", "0"],
    ]

    # Append new subscriptions
    data.extend(new_subscriptions)

    # Write back
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✓ Added days_overdue column and 3 subscriptions to {csv_path.name}")
    return csv_path


def add_tickets_with_notes():
    """Add notes column and 6 demo ticket rows"""
    csv_path = DB_DIR / "ravenstack_support_tickets.csv"

    # Read existing data
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    # Add notes column to header
    header.append("notes")

    # Add empty notes to all existing rows
    for row in data:
        row.append("")

    # New demo tickets (Nimbus - 4, Orion - 2)
    new_tickets = [
        # Nimbus tickets (product friction)
        ["T-NIM001", "A-NIMBUS", "2024-12-20", "", "0", "high", "120", "2.0", "True", "Dashboard crashes when loading large datasets"],
        ["T-NIM002", "A-NIMBUS", "2024-12-22", "", "0", "urgent", "180", "2.0", "True", "Export feature not working for 3 weeks"],
        ["T-NIM003", "A-NIMBUS", "2024-12-28", "", "0", "high", "90", "1.0", "False", "API response times degraded significantly"],
        ["T-NIM004", "A-NIMBUS", "2025-01-02", "", "0", "medium", "150", "2.0", "False", "Team unable to complete onboarding workflow"],
        # Orion tickets (competitor mention)
        ["T-ORI001", "A-ORION", "2024-12-15", "2024-12-16 10:00:00", "34.0", "high", "45", "1.0", "False", "Performance issues compared to competitors. Team is evaluating competitor solutions."],
        ["T-ORI002", "A-ORION", "2024-12-28", "", "0", "urgent", "200", "2.0", "True", "Critical workflow broken - considering alternative platforms"],
    ]

    # Append new tickets
    data.extend(new_tickets)

    # Write back
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✓ Added notes column and 6 tickets to {csv_path.name}")
    return csv_path


def add_feature_usage():
    """Add 16 demo usage rows"""
    csv_path = DB_DIR / "ravenstack_feature_usage.csv"

    # Read existing data
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    header = rows[0]
    data = rows[1:]

    # New demo usage data
    new_usage = [
        # Nimbus - 6 weeks ago (high usage)
        ["U-NIM001", "S-NIMBUS", "2024-11-20", "feature_1", "45", "18000", "0", "False"],
        ["U-NIM002", "S-NIMBUS", "2024-11-25", "feature_3", "38", "15200", "0", "False"],
        ["U-NIM003", "S-NIMBUS", "2024-11-30", "feature_5", "42", "16800", "1", "False"],
        ["U-NIM004", "S-NIMBUS", "2024-12-05", "feature_1", "40", "16000", "0", "False"],
        # Nimbus - recent 3 weeks (60% drop)
        ["U-NIM005", "S-NIMBUS", "2024-12-15", "feature_1", "15", "6000", "2", "False"],
        ["U-NIM006", "S-NIMBUS", "2024-12-20", "feature_3", "12", "4800", "3", "False"],
        ["U-NIM007", "S-NIMBUS", "2024-12-25", "feature_5", "18", "7200", "2", "False"],
        ["U-NIM008", "S-NIMBUS", "2025-01-01", "feature_1", "10", "4000", "4", "False"],
        # Vertex - healthy usage
        ["U-VTX001", "S-VERTEX", "2024-11-20", "feature_1", "30", "12000", "0", "False"],
        ["U-VTX002", "S-VERTEX", "2024-12-01", "feature_1", "32", "12800", "0", "False"],
        ["U-VTX003", "S-VERTEX", "2024-12-15", "feature_1", "35", "14000", "0", "False"],
        ["U-VTX004", "S-VERTEX", "2025-01-01", "feature_1", "33", "13200", "0", "False"],
        # Orion - moderate usage
        ["U-ORI001", "S-ORION", "2024-11-20", "feature_1", "25", "10000", "1", "False"],
        ["U-ORI002", "S-ORION", "2024-12-01", "feature_1", "22", "8800", "1", "False"],
        ["U-ORI003", "S-ORION", "2024-12-15", "feature_1", "20", "8000", "2", "False"],
        ["U-ORI004", "S-ORION", "2025-01-01", "feature_1", "18", "7200", "2", "False"],
    ]

    # Append new usage
    data.extend(new_usage)

    # Write back
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

    print(f"✓ Added 16 usage rows to {csv_path.name}")
    return csv_path


def verify_changes():
    """Print last 5 rows of each modified CSV"""
    print("\n" + "="*60)
    print("VERIFICATION - Last 5 rows of each modified CSV")
    print("="*60)

    files = [
        "ravenstack_accounts.csv",
        "ravenstack_subscriptions.csv",
        "ravenstack_support_tickets.csv",
        "ravenstack_feature_usage.csv",
    ]

    for filename in files:
        csv_path = DB_DIR / filename
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)

        print(f"\n--- {filename} (last 5 rows) ---")
        print(f"Header: {rows[0]}")
        for row in rows[-5:]:
            print(row)


def main():
    print("Adding demo accounts to CSV files...\n")

    # Add demo data
    add_demo_accounts()
    add_subscriptions_with_overdue()
    add_tickets_with_notes()
    add_feature_usage()

    # Verify
    verify_changes()

    print("\n" + "="*60)
    print("✅ All demo accounts added successfully!")
    print("="*60)


if __name__ == "__main__":
    main()
