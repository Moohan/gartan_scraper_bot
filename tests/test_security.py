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


def test_production_safeguard():
    """Verify that the Flask development server does not run in production."""
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["FLASK_ENV"] = "production"

    try:
        # Run api_server.py as a separate process
        # It should exit immediately with code 1 if safeguard works
        # Use a list of static strings to satisfy security scanners
        # sourcery skip: subprocess-run-pre-check
        result = subprocess.run(
            ["python3", "api_server.py"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
        )
        assert result.returncode == 1
        assert "Do not run the development server in production" in result.stdout
    except subprocess.TimeoutExpired:
        pytest.fail("Production safeguard failed - server kept running.")
