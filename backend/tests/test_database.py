"""
test_database.py - Tests for the database module

Run with: python -m pytest backend/tests/test_database.py -v
"""

import sys
from pathlib import Path

# Add backend to path so we can import database
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    init_database,
    get_all_accounts,
    get_account_by_id,
    get_account_tickets,
    get_usage_trend,
    get_ticket_stats,
    save_review_result,
    get_latest_review,
    log_action,
    get_action_log,
    DB_PATH,
)


class TestDatabaseInit:
    """Test database initialization."""

    def test_init_creates_database_file(self):
        """Database file should be created after init."""
        init_database()
        assert DB_PATH.exists(), "Database file should exist after initialization"

    def test_init_loads_all_csvs(self):
        """All CSV tables should be populated."""
        init_database()
        accounts = get_all_accounts()
        assert len(accounts) > 0, "Should have loaded accounts from CSV"


class TestAccountQueries:
    """Test account query functions."""

    def test_get_all_accounts_returns_list(self):
        """get_all_accounts should return a list of dicts."""
        init_database()
        accounts = get_all_accounts()

        assert isinstance(accounts, list)
        assert len(accounts) > 0
        assert isinstance(accounts[0], dict)

    def test_get_all_accounts_has_required_fields(self):
        """Each account should have the expected fields."""
        init_database()
        accounts = get_all_accounts()
        first = accounts[0]

        required_fields = [
            "account_id", "account_name", "industry", "plan_tier",
            "mrr_amount", "arr_amount"
        ]
        for field in required_fields:
            assert field in first, f"Account should have '{field}' field"

    def test_get_account_by_id_returns_account(self):
        """get_account_by_id should return a single account."""
        init_database()
        accounts = get_all_accounts()
        first_id = accounts[0]["account_id"]

        account = get_account_by_id(first_id)
        assert account is not None
        assert account["account_id"] == first_id

    def test_get_account_by_id_returns_none_for_invalid(self):
        """get_account_by_id should return None for non-existent ID."""
        init_database()
        account = get_account_by_id("INVALID-ID-12345")
        assert account is None


class TestTicketQueries:
    """Test support ticket query functions."""

    def test_get_account_tickets_returns_list(self):
        """get_account_tickets should return a list."""
        init_database()
        accounts = get_all_accounts()
        first_id = accounts[0]["account_id"]

        tickets = get_account_tickets(first_id)
        assert isinstance(tickets, list)

    def test_get_ticket_stats_returns_stats(self):
        """get_ticket_stats should return count, escalations, min_satisfaction."""
        init_database()
        accounts = get_all_accounts()
        first_id = accounts[0]["account_id"]

        stats = get_ticket_stats(first_id)
        assert "count" in stats
        assert "escalations" in stats
        assert "min_satisfaction" in stats


class TestUsageQueries:
    """Test feature usage query functions."""

    def test_get_usage_trend_returns_trend(self):
        """get_usage_trend should return recent, previous, change_pct."""
        init_database()
        accounts = get_all_accounts()
        first_id = accounts[0]["account_id"]

        trend = get_usage_trend(first_id)
        assert "recent" in trend
        assert "previous" in trend
        assert "change_pct" in trend


class TestReviewResults:
    """Test review results save/retrieve functions."""

    def test_save_and_retrieve_review(self):
        """Should be able to save and retrieve a review result."""
        init_database()
        accounts = get_all_accounts()
        first_id = accounts[0]["account_id"]

        mock_analysis = {
            "churn_risk_score": 75,
            "risk_reasons": ["Usage dropped", "Tickets increased"],
            "next_best_action": "training_call",
            "action_reasoning": "Customer needs help",
            "why_not_others": "No billing issues",
            "generated_email": "Dear customer...",
            "internal_memo": "Priority: HIGH",
            "slack_message": "Alert: Account at risk",
            "urgency_deadline": "48 hours"
        }

        result_id = save_review_result(first_id, 35, mock_analysis, "auto", "pending")
        assert result_id > 0

        retrieved = get_latest_review(first_id)
        assert retrieved is not None
        assert retrieved["account_id"] == first_id
        assert retrieved["health_score"] == 35
        assert retrieved["autonomy_level"] == "auto"


class TestActionLog:
    """Test action logging functions."""

    def test_log_and_retrieve_action(self):
        """Should be able to log and retrieve actions."""
        init_database()
        accounts = get_all_accounts()
        first_id = accounts[0]["account_id"]

        log_id = log_action(first_id, "slack_alert", "Sent to #retention-alerts", True)
        assert log_id > 0

        actions = get_action_log(first_id)
        assert len(actions) > 0
        assert actions[0]["action_type"] == "slack_alert"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
