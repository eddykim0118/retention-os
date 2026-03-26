"""
test_agent.py - Tests for Claude API agent

Run with: python -m pytest backend/tests/test_agent.py -v

To test the real Claude API:
    python -m pytest backend/tests/test_agent.py -v -k "real_api" --run-real-api
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import (
    mock_analyze_account,
    build_account_signals,
    analyze_account,
    ANALYSIS_TOOL,
)
from database import init_database, get_all_accounts


class TestAnalysisTool:
    """Test the tool schema definition."""

    def test_tool_has_required_fields(self):
        """Tool schema should have all required fields."""
        schema = ANALYSIS_TOOL["input_schema"]
        required = schema["required"]

        expected = [
            "churn_risk_score", "risk_reasons", "next_best_action",
            "action_reasoning", "why_not_others", "generated_email",
            "internal_memo", "slack_message", "urgency_deadline"
        ]
        for field in expected:
            assert field in required, f"Missing required field: {field}"

    def test_next_best_action_has_valid_enum(self):
        """next_best_action should have valid enum values."""
        schema = ANALYSIS_TOOL["input_schema"]
        enum_values = schema["properties"]["next_best_action"]["enum"]

        expected = ["training_call", "support_escalation", "finance_reminder", "senior_outreach"]
        assert set(enum_values) == set(expected)


class TestBuildAccountSignals:
    """Test building signals dict for Claude."""

    def test_build_signals_returns_dict(self):
        """build_account_signals should return a dict."""
        init_database()
        accounts = get_all_accounts()

        if accounts:
            account = accounts[0]
            signals = build_account_signals(account, health_score=50, risk_reasons=["Test reason"])

            assert isinstance(signals, dict)

    def test_signals_has_required_fields(self):
        """Signals dict should have all required fields."""
        init_database()
        accounts = get_all_accounts()

        if accounts:
            account = accounts[0]
            signals = build_account_signals(account, health_score=50, risk_reasons=["Test"])

            required = [
                "account_name", "health_score", "risk_reasons",
                "usage_trend", "ticket_stats"
            ]
            for field in required:
                assert field in signals, f"Missing field: {field}"


class TestMockAnalyze:
    """Test the mock analysis function (no API needed)."""

    def test_mock_returns_dict(self):
        """mock_analyze_account should return a dict."""
        signals = {
            "account_name": "Test Company",
            "health_score": 35,
            "arr_amount": 50000,
            "risk_reasons": ["Usage dropped"],
            "ticket_stats": {"escalations": 0},
            "usage_trend": {"change_percent": -40}
        }

        result = mock_analyze_account(signals)

        assert isinstance(result, dict)

    def test_mock_has_required_fields(self):
        """Mock result should have all required fields."""
        signals = {
            "account_name": "Test Company",
            "health_score": 35,
            "risk_reasons": ["Test"],
        }

        result = mock_analyze_account(signals)

        required = [
            "churn_risk_score", "risk_reasons", "next_best_action",
            "action_reasoning", "why_not_others", "generated_email",
            "internal_memo", "slack_message", "urgency_deadline"
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_mock_escalation_action(self):
        """Should recommend support_escalation when tickets are escalated."""
        signals = {
            "account_name": "Test",
            "health_score": 40,
            "ticket_stats": {"escalations": 2}
        }

        result = mock_analyze_account(signals)

        assert result["next_best_action"] == "support_escalation"

    def test_mock_training_action(self):
        """Should recommend training_call when usage drops significantly."""
        signals = {
            "account_name": "Test",
            "health_score": 40,
            "ticket_stats": {"escalations": 0},
            "usage_trend": {"change_percent": -50}
        }

        result = mock_analyze_account(signals)

        assert result["next_best_action"] == "training_call"

    def test_mock_senior_action_for_high_value(self):
        """Should recommend senior_outreach for high-value accounts."""
        signals = {
            "account_name": "Test",
            "health_score": 40,
            "arr_amount": 100000,
            "ticket_stats": {"escalations": 0},
            "usage_trend": {"change_percent": -10}
        }

        result = mock_analyze_account(signals)

        assert result["next_best_action"] == "senior_outreach"


class TestRealAPI:
    """Test the real Claude API (only runs with --run-real-api flag)."""

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_real_api_returns_analysis(self):
        """
        Test that the real Claude API returns a valid analysis.

        This test is skipped unless ANTHROPIC_API_KEY is set.
        """
        signals = {
            "account_name": "Nimbus Analytics",
            "industry": "DevTools",
            "plan_tier": "Enterprise",
            "seats": 45,
            "mrr_amount": 3000,
            "arr_amount": 36000,
            "health_score": 35,
            "risk_reasons": [
                "Usage dropped 60% in last 30 days",
                "4 support tickets in last 30 days",
                "2 tickets escalated"
            ],
            "usage_trend": {
                "recent_30d": 4000,
                "previous_30d": 10000,
                "change_percent": -60
            },
            "ticket_stats": {
                "count_last_30d": 4,
                "escalations": 2,
                "min_satisfaction_score": 2
            }
        }

        result = analyze_account(signals)

        # Should return a dict (not None)
        assert result is not None, "API should return a result"
        assert isinstance(result, dict)

        # Should have all required fields
        required = ["churn_risk_score", "next_best_action", "slack_message"]
        for field in required:
            assert field in result, f"Missing field: {field}"

        # Churn risk should be reasonable given health score of 35
        assert result["churn_risk_score"] >= 50, "Should have high churn risk"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
