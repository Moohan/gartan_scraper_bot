#!/usr/bin/env python3
"""Security tests for the API server."""

import pytest
from api_server import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_security_headers_present(client):
    """Verify that essential security headers are present in the response."""
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp
    assert "img-src 'self' data:" in csp

def test_permissions_policy_present(client):
    """Verify that the Permissions-Policy header is present."""
    response = client.get("/health")
    policy = response.headers.get("Permissions-Policy", "")
    assert "camera=()" in policy
    assert "microphone=()" in policy
    assert "geolocation=()" in policy
