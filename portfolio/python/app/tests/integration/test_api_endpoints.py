"""
Integration tests for Portfolia API endpoints.

This module contains comprehensive tests for all API endpoints based on manual testing.
Tests cover core API, authentication, market data, and statistical indicators.
"""

import pytest
from fastapi.testclient import TestClient


class TestCoreAPIEndpoints:
    """Test core API endpoints."""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Welcome to Portfolia API"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "health" in data

    def test_health_endpoint(self, client: TestClient):
        """Liveness does not depend on Postgres or Redis."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_api_v1_root(self, client: TestClient):
        """Test API v1 root endpoint."""
        response = client.get("/app/v1/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["router"] == "test_router"


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_user_registration_success(self, client: TestClient):
        """Test successful user registration."""
        user_data = {
            "username": "testuser_integration",
            "email": "test_integration@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }

        response = client.post("/app/v1/auth/register", json=user_data)
        assert response.status_code == 201

        data = response.json()
        assert data["username"] == "testuser_integration"
        assert data["email"] == "test_integration@example.com"
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_user_registration_duplicate_username(self, client: TestClient):
        """Test registration with duplicate username fails."""
        # First registration
        user_data = {
            "username": "duplicate_user",
            "email": "unique1@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }
        response = client.post("/app/v1/auth/register", json=user_data)
        assert response.status_code == 201

        # Second registration with same username
        user_data2 = {
            "username": "duplicate_user",
            "email": "unique2@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }
        response2 = client.post("/app/v1/auth/register", json=user_data2)
        assert response2.status_code == 400
        assert "Username already taken" in response2.json()["detail"]

    def test_user_registration_duplicate_email(self, client: TestClient):
        """Test registration with duplicate email fails."""
        # First registration
        user_data = {
            "username": "unique_user1",
            "email": "duplicate@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }
        response = client.post("/app/v1/auth/register", json=user_data)
        assert response.status_code == 201

        # Second registration with same email
        user_data2 = {
            "username": "unique_user2",
            "email": "duplicate@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }
        response2 = client.post("/app/v1/auth/register", json=user_data2)
        assert response2.status_code == 400
        assert "Email already registered" in response2.json()["detail"]

    def test_user_registration_missing_confirm_password(self, client: TestClient):
        """Test registration fails without confirm_password."""
        user_data = {
            "username": "testuser_missing",
            "email": "test_missing@example.com",
            "password": "TestPass123!",
        }

        response = client.post("/app/v1/auth/register", json=user_data)
        assert response.status_code == 422

        data = response.json()
        assert "confirm_password" in str(data["detail"])

    def test_user_login_success_with_username(self, client: TestClient):
        """Test successful login with username."""
        # First register a user
        user_data = {
            "username": "login_test_user",
            "email": "login_test@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }
        client.post("/app/v1/auth/register", json=user_data)

        # Then login with username
        login_data = {"username": "login_test_user", "password": "TestPass123!"}

        response = client.post("/app/v1/auth/login", json=login_data)
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_user_login_fails_with_email(self, client: TestClient):
        """Test login fails when using email instead of username."""
        login_data = {"email": "login_test@example.com", "password": "TestPass123!"}

        response = client.post("/app/v1/auth/login", json=login_data)
        assert response.status_code == 422

        data = response.json()
        assert "username" in str(data["detail"])

    def test_user_login_invalid_credentials(self, client: TestClient):
        """Test login fails with invalid credentials."""
        login_data = {"username": "nonexistent_user", "password": "wrongpassword"}

        response = client.post("/app/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_protected_endpoint_with_valid_token(self, client: TestClient):
        """Test accessing protected endpoint with valid JWT token."""
        # Register and login to get token
        user_data = {
            "username": "protected_test_user",
            "email": "protected_test@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }
        client.post("/app/v1/auth/register", json=user_data)

        login_data = {"username": "protected_test_user", "password": "TestPass123!"}
        login_response = client.post("/app/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Test protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/app/v1/auth/me", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert data["username"] == "protected_test_user"
        assert data["email"] == "protected_test@example.com"

    def test_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoint without token fails."""
        response = client.get("/app/v1/auth/me")
        assert response.status_code == 401

    def test_forgot_password_endpoint(self, client: TestClient):
        """Test forgot password endpoint."""
        response = client.post(
            "/app/v1/auth/forgot-password", json={"email": "test@example.com"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "password reset link has been sent" in data["message"]

    def test_logout_endpoint(self, client: TestClient):
        """Test logout endpoint."""
        # Register and login to get token
        user_data = {
            "username": "logout_test_user",
            "email": "logout_test@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }
        client.post("/app/v1/auth/register", json=user_data)

        login_data = {"username": "logout_test_user", "password": "TestPass123!"}
        login_response = client.post("/app/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Test logout
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/app/v1/auth/logout", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "Successfully logged out" in data["message"]


class TestMarketDataEndpoints:
    """Test market data endpoints."""

    def test_market_symbols_endpoint(self, client: TestClient):
        """Test market symbols endpoint."""
        response = client.get("/app/v1/market/symbols?name=AAPL")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Check structure of first item
        first_symbol = data[0]
        assert "symbol" in first_symbol
        assert "quoteType" in first_symbol

    def test_market_symbols_missing_name_parameter(self, client: TestClient):
        """Test market symbols endpoint fails without name parameter."""
        response = client.get("/app/v1/market/symbols")
        assert response.status_code == 422

        data = response.json()
        assert "name" in str(data["detail"])

    def test_market_symbol_data_endpoint_available(self, client: TestClient):
        """Test market symbol data endpoint is available."""
        # This endpoint might require more complex setup, so just check it exists
        response = client.get("/app/v1/market/symbol-data?name=AAPL&period=1d")
        # Should either return data or a specific error, but not 404
        assert response.status_code != 404


class TestStatisticalIndicatorsEndpoints:
    """Test statistical indicators endpoints."""

    def test_rsi_indicator_endpoint_available(self, client: TestClient):
        """Test RSI indicator endpoint is available."""
        response = client.get(
            "/app/v1/statistical-indicators/momentum-rsi-indicator?name=AAPL&period=14"
        )
        # Should either return data or a specific error, but not 404
        assert response.status_code != 404

    def test_rsi_indicator_missing_parameters(self, client: TestClient):
        """Test RSI indicator endpoint fails without required parameters."""
        response = client.get("/app/v1/statistical-indicators/momentum-rsi-indicator")
        assert response.status_code == 422


class TestAPIEndpointsComprehensive:
    """Comprehensive test suite for all API endpoints."""

    def test_all_auth_endpoints_available(self, client: TestClient):
        """Test that all authentication endpoints are available."""
        auth_endpoints = [
            "/app/v1/auth/register",
            "/app/v1/auth/login",
            "/app/v1/auth/logout",
            "/app/v1/auth/me",
            "/app/v1/auth/forgot-password",
            "/app/v1/auth/2fa/setup",
            "/app/v1/auth/2fa/verify",
            "/app/v1/auth/change-password",
            "/app/v1/auth/verify-email",
            "/app/v1/auth/reset-password",
        ]

        for endpoint in auth_endpoints:
            # Try to access each endpoint (some will require auth, but shouldn't be 404)
            response = (
                client.get(endpoint)
                if endpoint != "/app/v1/auth/register"
                else client.post(endpoint, json={})
            )
            assert response.status_code != 404, f"Endpoint {endpoint} not found"

    def test_api_documentation_available(self, client: TestClient):
        """Test that API documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/openapi.json")
        assert response.status_code == 200

        # Check that OpenAPI spec contains expected endpoints
        openapi_data = response.json()
        paths = openapi_data.get("paths", {})

        # Check for key endpoint categories
        auth_paths = [p for p in paths.keys() if "auth" in p]
        market_paths = [p for p in paths.keys() if "market" in p]
        indicator_paths = [p for p in paths.keys() if "indicators" in p]

        assert len(auth_paths) > 0, "No authentication endpoints found"
        assert len(market_paths) > 0, "No market endpoints found"
        assert len(indicator_paths) > 0, "No indicator endpoints found"

    def test_endpoint_parameter_validation(self, client: TestClient):
        """Test that endpoints properly validate required parameters."""
        # Test registration without required fields
        response = client.post("/app/v1/auth/register", json={})
        assert response.status_code == 422

        # Test login without required fields
        response = client.post("/app/v1/auth/login", json={})
        assert response.status_code == 422

        # Test market symbols without required parameter
        response = client.get("/app/v1/market/symbols")
        assert response.status_code == 422


class TestSecurityFeatures:
    """Test security features and constraints."""

    def test_password_strength_validation(self, client: TestClient):
        """Test that weak passwords are rejected."""
        user_data = {
            "username": "weak_pass_user",
            "email": "weak_pass@example.com",
            "password": "123",  # Too short
            "confirm_password": "123",
        }

        response = client.post("/app/v1/auth/register", json=user_data)
        assert response.status_code == 422

        data = response.json()
        assert "password" in str(data["detail"])

    def test_username_validation(self, client: TestClient):
        """Test that invalid usernames are rejected."""
        user_data = {
            "username": "invalid user",  # Contains space
            "email": "valid@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }

        response = client.post("/app/v1/auth/register", json=user_data)
        assert response.status_code == 422

        data = response.json()
        assert "username" in str(data["detail"])

    def test_jwt_token_expiration(self, client: TestClient):
        """Test that JWT tokens have proper expiration."""
        # Register and login to get token
        user_data = {
            "username": "token_test_user",
            "email": "token_test@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        }
        client.post("/app/v1/auth/register", json=user_data)

        login_data = {"username": "token_test_user", "password": "TestPass123!"}
        login_response = client.post("/app/v1/auth/login", json=login_data)
        token_data = login_response.json()

        # Check token structure
        assert "expires_in" in token_data
        assert token_data["expires_in"] > 0
        assert token_data["token_type"] == "bearer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
