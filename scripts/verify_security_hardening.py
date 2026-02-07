#!/usr/bin/env python3
"""Verification script for API security hardening."""

import os
import sys
import unittest

from api_server import app


class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_security_headers(self):
        """Verify that all expected security headers are present."""
        response = self.client.get("/health")  # health might be safer
        headers = response.headers

        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(
            headers.get("Strict-Transport-Security"),
            "max-age=31536000; includeSubDomains",
        )
        self.assertEqual(
            headers.get("Referrer-Policy"), "strict-origin-when-cross-origin"
        )

        csp = headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("base-uri 'self'", csp)
        self.assertIn("form-action 'self'", csp)
        self.assertIn("img-src 'self' data:", csp)

    def test_production_safeguard(self):
        """Verify that app.run() is protected by the FLASK_ENV check."""
        # This is a bit hard to test directly without executing the __main__ block,
        # but we can verify the logic exists in the file.
        with open("api_server.py", "r") as f:
            content = f.read()

        self.assertIn('if os.environ.get("FLASK_ENV") == "production":', content)
        self.assertIn("sys.exit(1)", content)
        self.assertIn("Use gunicorn instead.", content)

    def test_container_main_gunicorn(self):
        """Verify that container_main.py uses gunicorn."""
        with open("container_main.py", "r") as f:
            content = f.read()

        self.assertIn('"gunicorn"', content)
        self.assertIn("port_str.isdigit()", content)
        self.assertIn("subprocess.run", content)


if __name__ == "__main__":
    unittest.main()
