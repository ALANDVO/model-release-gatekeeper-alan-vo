"""Authentication, authorization, role enforcement, and OIDC PKCE integration tests."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.core.security import create_demo_token


def test_unauthenticated_request_rejected(client: TestClient):
    """Endpoints require authentication headers."""
    resp = client.get("/api/candidates")
    assert resp.status_code == 401
    assert "Missing Bearer" in resp.json()["detail"]


def test_invalid_token_rejected(client: TestClient):
    """Invalid bearer tokens are rejected."""
    headers = {"Authorization": "Bearer invalid.malformed.token"}
    resp = client.get("/api/candidates", headers=headers)
    assert resp.status_code == 401


def test_role_denial_viewer_cannot_create_candidate(client: TestClient, viewer_token: str):
    """Viewer role is denied write access to candidate registration."""
    headers = {"Authorization": f"Bearer {viewer_token}"}
    payload = {
        "name": "unauthorized-candidate",
        "version": "1.0.0",
        "task_type": "text-generation",
        "base_model": "llama-3-8b",
        "artifact_uri": "s3://models/candidate-1.bin",
        "artifact_hash": "a" * 64,
    }
    resp = client.post("/api/candidates", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "analyst" in resp.json()["detail"]


def test_role_denial_analyst_cannot_create_policy(client: TestClient, analyst_token: str):
    """Analyst role is denied policy administration privileges."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    payload = {
        "name": "unauthorized-policy",
        "task_type": "text-generation",
        "rules": [{"metric_name": "acc", "operator": ">=", "threshold": 0.8, "severity": "blocker"}]
    }
    resp = client.post("/api/policies", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"]


def test_production_refusal_of_demo_mode():
    """Startup refuses demo mode when environment is production."""
    with pytest.raises(RuntimeError, match="Demo mode cannot be enabled in production"):
        Settings(ENVIRONMENT="production", DEMO_MODE=True)


def test_demo_login_flow(client: TestClient):
    """Local demo login issues valid role-scoped tokens."""
    resp = client.post(
        "/api/auth/demo-login",
        json={"username": "test-analyst", "email": "analyst@example.com", "role": "analyst"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "analyst"

    # Use the issued demo token to authenticate
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    userinfo = client.get("/api/auth/userinfo", headers=headers)
    assert userinfo.status_code == 200
    assert userinfo.json()["username"] == "test-analyst"
    assert userinfo.json()["role"] == "analyst"


@pytest.mark.asyncio
async def test_oidc_pkce_exchange_and_token_propagation(client: TestClient):
    """Test full OIDC code + PKCE exchange and subsequent authorized API request."""
    demo_jwt = create_demo_token(username="oidc-operator", email="operator@example.com", role="analyst")

    mock_token_resp = {
        "access_token": demo_jwt,
        "token_type": "Bearer",
        "expires_in": 3600,
        "id_token": "mock-id-token",
    }

    with patch("app.api.auth.exchange_authorization_code", new_callable=AsyncMock) as mock_exchange:
        mock_exchange.return_value = mock_token_resp

        # Call token exchange endpoint with PKCE parameters
        exchange_req = {
            "code": "test-auth-code-12345",
            "code_verifier": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            "redirect_uri": "http://127.0.0.1:5173/callback"
        }
        res = client.post("/api/auth/token", json=exchange_req)
        assert res.status_code == 200
        token_data = res.json()
        assert token_data["access_token"] == demo_jwt

        # Use the exchanged token in an authorized request crossing real HTTP boundary
        auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        userinfo_res = client.get("/api/auth/userinfo", headers=auth_headers)
        assert userinfo_res.status_code == 200
        assert userinfo_res.json()["username"] == "oidc-operator"
        assert userinfo_res.json()["role"] == "analyst"
