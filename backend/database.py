"""
database.py - SQLite database setup and CSV loader

This module handles:
1. Loading all RavenStack CSVs into SQLite on startup
2. Creating additional tables for review results and action logs
3. Providing query helper functions for the rest of the app
"""

import csv
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


# Reference date for "last 30 days" calculations
# The dataset spans 2023-2024, so we use a fixed date instead of datetime.now()
REFERENCE_DATE = datetime(2025, 1, 1)

# Database file path
DB_PATH = Path(__file__).parent / "db" / "retention.db"
CSV_DIR = Path(__file__).parent / "db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This lets us access columns by name
    return conn


def init_database():
    """Initialize the database: load CSVs and create app tables."""
    print("[DB] Initializing database...")

    conn = get_connection()
    cursor = conn.cursor()

    # Load all CSV files into SQLite
    _load_csv_to_table(cursor, "accounts", "ravenstack_accounts.csv")
    _load_csv_to_table(cursor, "subscriptions", "ravenstack_subscriptions.csv")
    _load_csv_to_table(cursor, "support_tickets", "ravenstack_support_tickets.csv")
    _load_csv_to_table(cursor, "feature_usage", "ravenstack_feature_usage.csv")
    _load_csv_to_table(cursor, "churn_events", "ravenstack_churn_events.csv")

    # Create app-specific tables
    _create_app_tables(cursor)

    conn.commit()
    conn.close()
    print("[DB] Database initialization complete.")


def _load_csv_to_table(cursor: sqlite3.Cursor, table_name: str, csv_filename: str):
    """Load a CSV file into a SQLite table."""
    csv_path = CSV_DIR / csv_filename

    if not csv_path.exists():
        print(f"[DB] WARNING: {csv_filename} not found, skipping...")
        return

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames

        if not columns:
            print(f"[DB] WARNING: {csv_filename} has no columns, skipping...")
            return

        # Drop existing table and create new one
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        # Create table with all columns as TEXT (simple approach for hackathon)
        columns_sql = ", ".join([f'"{col}" TEXT' for col in columns])
        cursor.execute(f"CREATE TABLE {table_name} ({columns_sql})")

        # Insert all rows
        placeholders = ", ".join(["?" for _ in columns])
        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"

        row_count = 0
        for row in reader:
            values = [row[col] for col in columns]
            cursor.execute(insert_sql, values)
            row_count += 1

        print(f"[DB] Loaded {row_count} rows into {table_name}")


def _create_app_tables(cursor: sqlite3.Cursor):
    """Create tables for storing review results and action logs."""

    # review_results: stores Claude's analysis for each account
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            reviewed_at TEXT NOT NULL,
            health_score INTEGER,
            churn_risk_score INTEGER,
            risk_reasons TEXT,
            next_best_action TEXT,
            action_reasoning TEXT,
            why_not_others TEXT,
            generated_email TEXT,
            internal_memo TEXT,
            slack_message TEXT,
            urgency_deadline TEXT,
            autonomy_level TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    print("[DB] Created review_results table")

    # action_log: stores what actions the AI actually took
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            action_detail TEXT,
            executed_at TEXT NOT NULL,
            success INTEGER DEFAULT 1
        )
    """)
    print("[DB] Created action_log table")


# =============================================================================
# QUERY HELPERS
# =============================================================================

def get_all_accounts() -> list[dict]:
    """Get all accounts with their subscription info."""
    conn = get_connection()
    cursor = conn.cursor()

    # Some accounts have multiple active subscription rows in the seed data.
    # Pick the latest active row per account so the account list stays unique.
    cursor.execute("""
        WITH ranked_subscriptions AS (
            SELECT
                s.*,
                ROW_NUMBER() OVER (
                    PARTITION BY s.account_id
                    ORDER BY s.start_date DESC, s.subscription_id DESC
                ) AS rn
            FROM subscriptions s
            WHERE s.end_date IS NULL OR s.end_date = ''
        )
        SELECT
            a.account_id,
            a.account_name,
            a.industry,
            a.country,
            a.plan_tier,
            a.seats,
            a.is_trial,
            a.churn_flag,
            s.subscription_id,
            s.mrr_amount,
            s.arr_amount,
            s.downgrade_flag,
            s.days_overdue,
            s.start_date,
            s.end_date
        FROM accounts a
        LEFT JOIN ranked_subscriptions s
            ON a.account_id = s.account_id
            AND s.rn = 1
        ORDER BY a.account_id
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_account_by_id(account_id: str) -> Optional[dict]:
    """Get a single account with full details."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        WITH ranked_subscriptions AS (
            SELECT
                s.*,
                ROW_NUMBER() OVER (
                    PARTITION BY s.account_id
                    ORDER BY s.start_date DESC, s.subscription_id DESC
                ) AS rn
            FROM subscriptions s
            WHERE s.end_date IS NULL OR s.end_date = ''
        )
        SELECT
            a.account_id,
            a.account_name,
            a.industry,
            a.country,
            a.plan_tier,
            a.seats,
            a.is_trial,
            a.churn_flag,
            s.subscription_id,
            s.mrr_amount,
            s.arr_amount,
            s.downgrade_flag,
            s.days_overdue,
            s.start_date,
            s.end_date
        FROM accounts a
        LEFT JOIN ranked_subscriptions s
            ON a.account_id = s.account_id
            AND s.rn = 1
        WHERE a.account_id = ?
    """, (account_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_account_tickets(account_id: str, days: int = 30) -> list[dict]:
    """Get support tickets for an account within the last N days."""
    conn = get_connection()
    cursor = conn.cursor()

    cutoff_date = (REFERENCE_DATE - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT *
        FROM support_tickets
        WHERE account_id = ?
        AND submitted_at >= ?
        ORDER BY submitted_at DESC
    """, (account_id, cutoff_date))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_account_usage(account_id: str, days: int = 30) -> list[dict]:
    """
    Get feature usage for an account within the last N days.
    Note: feature_usage links to subscription_id, so we need to JOIN through subscriptions.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cutoff_date = (REFERENCE_DATE - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT fu.*
        FROM feature_usage fu
        JOIN subscriptions s ON fu.subscription_id = s.subscription_id
        WHERE s.account_id = ?
        AND fu.usage_date >= ?
        ORDER BY fu.usage_date DESC
    """, (account_id, cutoff_date))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_usage_trend(account_id: str) -> dict:
    """
    Compare usage in recent 30 days vs previous 30 days.
    Returns: {"recent": total_count, "previous": total_count, "change_pct": float}
    """
    conn = get_connection()
    cursor = conn.cursor()

    recent_start = (REFERENCE_DATE - timedelta(days=30)).strftime("%Y-%m-%d")
    previous_start = (REFERENCE_DATE - timedelta(days=60)).strftime("%Y-%m-%d")
    previous_end = (REFERENCE_DATE - timedelta(days=30)).strftime("%Y-%m-%d")

    # Recent 30 days
    cursor.execute("""
        SELECT COALESCE(SUM(CAST(fu.usage_count AS INTEGER)), 0) as total
        FROM feature_usage fu
        JOIN subscriptions s ON fu.subscription_id = s.subscription_id
        WHERE s.account_id = ?
        AND fu.usage_date >= ?
    """, (account_id, recent_start))
    recent = cursor.fetchone()["total"]

    # Previous 30 days
    cursor.execute("""
        SELECT COALESCE(SUM(CAST(fu.usage_count AS INTEGER)), 0) as total
        FROM feature_usage fu
        JOIN subscriptions s ON fu.subscription_id = s.subscription_id
        WHERE s.account_id = ?
        AND fu.usage_date >= ? AND fu.usage_date < ?
    """, (account_id, previous_start, previous_end))
    previous = cursor.fetchone()["total"]

    conn.close()

    # Calculate percentage change
    if previous > 0:
        change_pct = ((recent - previous) / previous) * 100
    else:
        change_pct = 0 if recent == 0 else 100

    return {
        "recent": recent,
        "previous": previous,
        "change_pct": round(change_pct, 1)
    }


def get_ticket_stats(account_id: str, days: int = 30) -> dict:
    """
    Get ticket statistics for an account.
    Returns: {"count": int, "escalations": int, "min_satisfaction": float}
    """
    conn = get_connection()
    cursor = conn.cursor()

    cutoff_date = (REFERENCE_DATE - timedelta(days=days)).strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT
            COUNT(*) as count,
            SUM(CASE WHEN escalation_flag = 'True' THEN 1 ELSE 0 END) as escalations,
            MIN(CASE WHEN satisfaction_score != '' THEN CAST(satisfaction_score AS REAL) END) as min_satisfaction
        FROM support_tickets
        WHERE account_id = ?
        AND submitted_at >= ?
    """, (account_id, cutoff_date))

    row = cursor.fetchone()
    conn.close()

    return {
        "count": row["count"] or 0,
        "escalations": row["escalations"] or 0,
        "min_satisfaction": row["min_satisfaction"]
    }


def save_review_result(
    account_id: str,
    health_score: int,
    analysis: dict,
    autonomy_level: str,
    status: str = "pending"
) -> int:
    """Save Claude's analysis result for an account."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO review_results (
            account_id, reviewed_at, health_score, churn_risk_score,
            risk_reasons, next_best_action, action_reasoning, why_not_others,
            generated_email, internal_memo, slack_message, urgency_deadline,
            autonomy_level, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        account_id,
        datetime.now().isoformat(),
        health_score,
        analysis.get("churn_risk_score"),
        str(analysis.get("risk_reasons", [])),
        analysis.get("next_best_action"),
        analysis.get("action_reasoning"),
        analysis.get("why_not_others"),
        analysis.get("generated_email"),
        analysis.get("internal_memo"),
        analysis.get("slack_message"),
        analysis.get("urgency_deadline"),
        autonomy_level,
        status
    ))

    result_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return result_id


def get_latest_review(account_id: str) -> Optional[dict]:
    """Get the most recent review result for an account."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM review_results
        WHERE account_id = ?
        ORDER BY reviewed_at DESC
        LIMIT 1
    """, (account_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def log_action(account_id: str, action_type: str, detail: str = "", success: bool = True) -> int:
    """Log an action taken by the AI."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO action_log (account_id, action_type, action_detail, executed_at, success)
        VALUES (?, ?, ?, ?, ?)
    """, (account_id, action_type, detail, datetime.now().isoformat(), 1 if success else 0))

    log_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return log_id


def get_action_log(account_id: str) -> list[dict]:
    """Get all actions taken for an account."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM action_log
        WHERE account_id = ?
        ORDER BY executed_at DESC
    """, (account_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_review_status(account_id: str, new_status: str):
    """Update the status of the latest review for an account."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE review_results
        SET status = ?
        WHERE account_id = ?
        AND id = (SELECT MAX(id) FROM review_results WHERE account_id = ?)
    """, (new_status, account_id, account_id))

    conn.commit()
    conn.close()


def get_reviewed_account_ids() -> set[str]:
    """Get the set of all account IDs that have been reviewed.

    This is used by the run_review endpoint to skip accounts
    that have already been analyzed, so subsequent runs
    process the NEXT batch of at-risk accounts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT account_id FROM review_results
    """)

    rows = cursor.fetchall()
    conn.close()

    return {row["account_id"] for row in rows}
