"""
test_routes.py - Tests for API routes

Run with: python -m pytest backend/tests/test_routes.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
from database import init_database, get_all_accounts


# Initialize database once for all tests
init_database()

# Create test client
client = TestClient(app)


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_returns_200(self):
        """Health endpoint should return 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status(self):
        """Health endpoint should return status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


class TestAccountsListEndpoint:
    """Test GET /api/accounts endpoint."""

    def test_returns_200(self):
        """Accounts list should return 200."""
        response = client.get("/api/accounts")
        assert response.status_code == 200

    def test_returns_list(self):
        """Accounts list should return a list."""
        response = client.get("/api/accounts")
        data = response.json()
        assert isinstance(data, list)

    def test_accounts_have_required_fields(self):
        """Each account should have required fields."""
        response = client.get("/api/accounts")
        data = response.json()

        if data:  # Only test if there are accounts
            first = data[0]
            required = ["account_id", "account_name", "health_score", "risk_level"]
            for field in required:
                assert field in first, f"Missing field: {field}"

    def test_accounts_sorted_by_health_score(self):
        """Accounts should be sorted by health score ascending."""
        response = client.get("/api/accounts")
        data = response.json()

        if len(data) > 1:
            scores = [a["health_score"] for a in data if a["health_score"] is not None]
            assert scores == sorted(scores), "Should be sorted by health score"


class TestAccountDetailEndpoint:
    """Test GET /api/accounts/{account_id} endpoint."""

    def test_returns_200_for_valid_id(self):
        """Should return 200 for valid account ID."""
        # Get a valid account ID first
        accounts = get_all_accounts()
        if accounts:
            account_id = accounts[0]["account_id"]
            response = client.get(f"/api/accounts/{account_id}")
            assert response.status_code == 200

    def test_returns_404_for_invalid_id(self):
        """Should return 404 for invalid account ID."""
        response = client.get("/api/accounts/INVALID-ID-12345")
        assert response.status_code == 404

    def test_detail_has_required_fields(self):
        """Account detail should have all required fields."""
        accounts = get_all_accounts()
        if accounts:
            account_id = accounts[0]["account_id"]
            response = client.get(f"/api/accounts/{account_id}")
            data = response.json()

            required = [
                "account_id", "account_name", "health_score", "risk_level",
                "autonomy_level", "autonomy_reason"
            ]
            for field in required:
                assert field in data, f"Missing field: {field}"

    def test_detail_has_risk_reasons(self):
        """Account detail should have risk_reasons list."""
        accounts = get_all_accounts()
        if accounts:
            account_id = accounts[0]["account_id"]
            response = client.get(f"/api/accounts/{account_id}")
            data = response.json()

            assert "risk_reasons" in data
            # risk_reasons can be None or a list
            if data["risk_reasons"] is not None:
                assert isinstance(data["risk_reasons"], list)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
