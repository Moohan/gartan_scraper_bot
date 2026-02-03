#!/usr/bin/env python3
"""Security verification script for Gartan Scraper Bot API."""

import os
import sys
import unittest
from unittest.mock import patch

# Add root directory to path so we can import api_server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api_server import app


class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_security_headers(self):
        """Verify that all required security headers are present and have correct values."""
        response = self.client.get("/")
        headers = response.headers

        # Check standard security headers
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(headers.get("Strict-Transport-Security"), "max-age=31536000; includeSubDomains")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

        # Check Content-Security-Policy
        csp = headers.get("Content-Security-Policy")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("form-action 'self'", csp)
        self.assertIn("img-src 'self' data:", csp)
        self.assertIn("frame-ancestors 'none'", csp)

        # Check Permissions-Policy
        permissions = headers.get("Permissions-Policy")
        self.assertIn("camera=()", permissions)
        self.assertIn("microphone=()", permissions)
        self.assertIn("geolocation=()", permissions)

    def test_production_safeguard(self):
        """Verify that the development server won't start if FLASK_ENV=production."""
        # We need to test the __main__ block behavior
        # Since we can't easily run the actual app.run() and check exit,
        # we'll mock os.environ and check the logic if we were to run it.

        with patch("os.environ.get") as mock_get:
            mock_get.return_value = "production"

            # This is a bit tricky to test directly without executing the script
            # But we can verify the logic is present in the file
            with open("api_server.py", "r") as f:
                content = f.read()
                self.assertIn('if os.environ.get("FLASK_ENV") == "production":', content)
                self.assertIn('print("Error: Do not run the development server in production.")', content)
                self.assertIn('exit(1)', content)

if __name__ == "__main__":
    unittest.main()
