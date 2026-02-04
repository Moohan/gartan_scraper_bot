#!/usr/bin/env python3
"""
Automated verification of API server security hardening.
Checks for HSTS, CSP, Referrer-Policy, and the production environment safeguard.
"""

import os
import subprocess
import time
import requests
import sys

def test_security_headers():
    print("Checking security headers...")
    # Start the server in a separate process
    # Use a non-standard port for testing
    port = "5005"
    env = os.environ.copy()
    env["PORT"] = port
    env["FLASK_ENV"] = "development" # Allow dev server for this test

    proc = subprocess.Popen(
        [sys.executable, "api_server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(2)

    try:
        response = requests.get(f"http://localhost:{port}/health")
        headers = response.headers

        checks = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        success = True
        for header, expected in checks.items():
            value = headers.get(header)
            if value == expected:
                print(f"  [PASS] {header}: {value}")
            else:
                print(f"  [FAIL] {header}: expected '{expected}', got '{value}'")
                success = False

        # Check CSP separately as it's complex
        csp = headers.get("Content-Security-Policy", "")
        csp_checks = [
            "default-src 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "img-src 'self' data:"
        ]

        for check in csp_checks:
            if check in csp:
                print(f"  [PASS] CSP contains: {check}")
            else:
                print(f"  [FAIL] CSP missing: {check}")
                success = False

        return success
    finally:
        proc.terminate()
        proc.wait()

def test_production_safeguard():
    print("\nChecking production safeguard...")
    port = "5006"
    env = os.environ.copy()
    env["PORT"] = port
    env["FLASK_ENV"] = "production"

    proc = subprocess.Popen(
        [sys.executable, "api_server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # It should exit quickly
        stdout, stderr = proc.communicate(timeout=5)
        if proc.returncode == 1 and "Do not run the development server in production" in stdout:
            print("  [PASS] Production safeguard triggered correctly.")
            return True
        else:
            print(f"  [FAIL] Production safeguard failed. Return code: {proc.returncode}")
            print(f"  STDOUT: {stdout}")
            return False
    except subprocess.TimeoutExpired:
        proc.kill()
        print("  [FAIL] Production safeguard failed - server kept running.")
        return False

if __name__ == "__main__":
    headers_ok = test_security_headers()
    safeguard_ok = test_production_safeguard()

    if headers_ok and safeguard_ok:
        print("\nOverall Status: [PASSED]")
        sys.exit(0)
    else:
        print("\nOverall Status: [FAILED]")
        sys.exit(1)
