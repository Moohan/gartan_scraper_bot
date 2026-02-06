#!/usr/bin/env python3
"""
Verification script for API server security hardening.
Checks security headers and the production safeguard.
"""

import os
import subprocess
import sys
import time
import requests

def test_security_headers():
    print("--- Testing Security Headers ---")
    # Start the server locally in development mode
    os.environ["FLASK_DEBUG"] = "true"
    os.environ["FLASK_ENV"] = "development"
    port = 5050
    process = subprocess.Popen(  # nosec
        [sys.executable, "api_server.py"],
        env={**os.environ, "PORT": str(port)},
    )

    # Wait for server to start
    time.sleep(3)

    try:
        url = f"http://localhost:{port}/health"
        response = requests.get(url)
        headers = response.headers

        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; img-src 'self' data:"
        }

        all_passed = True
        for header, expected_value in expected_headers.items():
            actual_value = headers.get(header)
            if actual_value == expected_value:
                print(f"[PASS] {header}")
            else:
                print(f"[FAIL] {header}: Expected '{expected_value}', got '{actual_value}'")
                all_passed = False

        return all_passed
    finally:
        process.terminate()
        process.wait()

def test_production_safeguard():
    print("\n--- Testing Production Safeguard ---")
    # Attempt to run the server with FLASK_ENV=production
    env = os.environ.copy()
    env["FLASK_ENV"] = "production"
    env["PORT"] = "5051"

    try:
        result = subprocess.run(  # nosec
            [sys.executable, "api_server.py"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        # It should exit with an error
        if result.returncode != 0 and "Do not run the development server in production" in result.stdout + result.stderr:
            print("[PASS] Production safeguard triggered correctly.")
            return True
        else:
            print(f"[FAIL] Production safeguard did not trigger as expected. Return code: {result.returncode}")
            print(f"Output: {result.stdout}\n{result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("[FAIL] Server kept running in production mode (timeout).")
        return False

if __name__ == "__main__":
    headers_ok = test_security_headers()
    safeguard_ok = test_production_safeguard()

    if headers_ok and safeguard_ok:
        print("\n✅ All security verifications passed!")
        sys.exit(0)
    else:
        print("\n❌ Security verification failed.")
        sys.exit(1)
