#!/usr/bin/env python3
"""
Test script for the Gartan Availability API

Tests all implemented endpoints against the specification
"""

import requests
import json
import sys
from datetime import datetime, timezone

API_BASE = "http://127.0.0.1:5000/v1"


def check_endpoint(method, url, expected_type=None, description=""):
    """Test an API endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {method} {url}")
    print(f"Description: {description}")
    print(f"{'='*60}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            print(f"ERROR: Method {method} not supported")
            return False

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response Type: {type(data).__name__}")
                print(f"Response Data: {json.dumps(data, indent=2)}")

                # Type checking
                if expected_type and not isinstance(data, expected_type):
                    print(
                        f"WARNING: Expected {expected_type.__name__}, got {type(data).__name__}"
                    )

                return True
            except json.JSONDecodeError:
                # For simple text responses
                print(f"Response (raw): {response.text}")
                return True
        else:
            print(f"Error Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server. Make sure it's running.")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Run all API tests"""
    print("🚀 Starting Gartan Availability API Tests")
    print(f"API Base URL: {API_BASE}")
    print(f"Current time: {datetime.now(timezone.utc).isoformat()}")

    tests = [
        # Phase 1: Essential endpoints
        ("GET", f"{API_BASE}/crew", list, "Get crew list"),
        (
            "GET",
            f"{API_BASE}/crew/1/available",
            bool,
            "Check if crew member 1 is available",
        ),
        (
            "GET",
            f"{API_BASE}/crew/5/available",
            bool,
            "Check if crew member 5 (MCMAHON, JA) is available",
        ),
        (
            "GET",
            f"{API_BASE}/appliances/P22P6/available",
            bool,
            "Check if appliance P22P6 is available",
        ),
        # Phase 2: Duration endpoints
        (
            "GET",
            f"{API_BASE}/crew/1/duration",
            (str, type(None)),
            "Get crew member 1 duration",
        ),
        (
            "GET",
            f"{API_BASE}/crew/5/duration",
            (str, type(None)),
            "Get crew member 5 duration",
        ),
        (
            "GET",
            f"{API_BASE}/appliances/P22P6/duration",
            (str, type(None)),
            "Get appliance P22P6 duration",
        ),
        # Error cases
        (
            "GET",
            f"{API_BASE}/crew/999/available",
            str,
            "Test invalid crew ID (should return 404)",
        ),
        (
            "GET",
            f"{API_BASE}/appliances/INVALID/available",
            str,
            "Test invalid appliance (should return 404)",
        ),
    ]

    passed = 0
    total = len(tests)

    for method, url, expected_type, description in tests:
        success = check_endpoint(method, url, expected_type, description)
        if success:
            passed += 1

    print(f"\n{'='*60}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"❌ {total - passed} test(s) failed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
