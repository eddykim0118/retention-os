"""
test_health_score.py - Tests for health score calculation

Run with: python -m pytest backend/tests/test_health_score.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_database, get_all_accounts
from health_score import (
    calculate_health_score,
    get_risk_level,
    get_autonomy_level,
    get_at_risk_accounts,
)


class TestHealthScoreCalculation:
    """Test health score calculation."""

    def test_calculate_health_score_returns_tuple(self):
        """Should return (score, reasons) tuple."""
        init_database()
        accounts = get_all_accounts()
        first_id = accounts[0]["account_id"]

        result = calculate_health_score(first_id)

        assert isinstance(result, tuple)
        assert len(result) == 2
        score, reasons = result
        assert isinstance(score, int)
        assert isinstance(reasons, list)

    def test_score_is_between_0_and_100(self):
        """Health score should be between 0 and 100."""
        init_database()
        accounts = get_all_accounts()

        for account in accounts[:10]:  # Test first 10
            score, _ = calculate_health_score(account["account_id"])
            assert 0 <= score <= 100, f"Score {score} out of range"


class TestRiskLevel:
    """Test risk level categorization."""

    def test_high_risk_below_40(self):
        """Score below 40 should be high risk."""
        assert get_risk_level(39) == "high"
        assert get_risk_level(0) == "high"
        assert get_risk_level(20) == "high"

    def test_medium_risk_40_to_70(self):
        """Score 40-70 should be medium risk."""
        assert get_risk_level(40) == "medium"
        assert get_risk_level(55) == "medium"
        assert get_risk_level(70) == "medium"

    def test_low_risk_above_70(self):
        """Score above 70 should be low risk."""
        assert get_risk_level(71) == "low"
        assert get_risk_level(85) == "low"
        assert get_risk_level(100) == "low"


class TestAutonomyLevel:
    """Test autonomy level determination."""

    def test_needs_approval_high_risk_high_value(self):
        """High risk + high ARR = needs approval."""
        level, reason = get_autonomy_level(health_score=35, arr_amount=100000)
        assert level == "needs_approval"
        assert "requires approval" in reason.lower()

    def test_auto_high_risk_low_value(self):
        """High risk + low ARR = auto (not valuable enough to bother humans)."""
        level, reason = get_autonomy_level(health_score=35, arr_amount=30000)
        assert level == "auto"
        assert "under $50K" in reason

    def test_auto_low_risk_high_value(self):
        """Low risk = auto (not critical enough)."""
        level, reason = get_autonomy_level(health_score=75, arr_amount=100000)
        assert level == "auto"
        assert "not critical" in reason.lower()

    def test_auto_low_risk_low_value(self):
        """Low risk + low ARR = auto."""
        level, reason = get_autonomy_level(health_score=80, arr_amount=10000)
        assert level == "auto"

    def test_boundary_50k_arr(self):
        """Test boundary at exactly $50K ARR."""
        # At boundary, should need approval
        level, _ = get_autonomy_level(health_score=35, arr_amount=50000)
        assert level == "needs_approval"

        # Just below, should be auto
        level, _ = get_autonomy_level(health_score=35, arr_amount=49999)
        assert level == "auto"


class TestAtRiskAccounts:
    """Test at-risk account filtering."""

    def test_get_at_risk_accounts_returns_list(self):
        """Should return a list of enriched accounts."""
        init_database()
        accounts = get_all_accounts()

        at_risk = get_at_risk_accounts(accounts, threshold=70)

        assert isinstance(at_risk, list)

    def test_at_risk_accounts_have_required_fields(self):
        """Each at-risk account should have health_score, risk_level, etc."""
        init_database()
        accounts = get_all_accounts()

        at_risk = get_at_risk_accounts(accounts, threshold=70)

        if at_risk:  # Only test if there are at-risk accounts
            first = at_risk[0]
            assert "health_score" in first
            assert "risk_level" in first
            assert "risk_reasons" in first
            assert "autonomy_level" in first
            assert "autonomy_reason" in first

    def test_at_risk_accounts_sorted_by_score(self):
        """At-risk accounts should be sorted by health score (worst first)."""
        init_database()
        accounts = get_all_accounts()

        at_risk = get_at_risk_accounts(accounts, threshold=70)

        if len(at_risk) > 1:
            scores = [a["health_score"] for a in at_risk]
            assert scores == sorted(scores), "Should be sorted ascending (worst first)"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
