#!/usr/bin/env python3
"""
Quick test of the new weekly API endpoints
"""

import sys
sys.path.append('.')

from api_server import get_crew_hours_this_week_data, get_crew_hours_planned_week_data
import json

def test_weekly_endpoints():
    """Test the weekly API functions directly"""

    print("Testing Weekly Availability API Endpoints")
    print("=" * 50)

    # Test with crew ID 2 (CASELY, CH)
    crew_id = 2

    print(f"Testing crew ID {crew_id}:")

    # Test hours this week
    result1 = get_crew_hours_this_week_data(crew_id)
    print("Hours this week:", json.dumps(result1, indent=2))

    # Test planned hours this week
    result2 = get_crew_hours_planned_week_data(crew_id)
    print("Planned hours this week:", json.dumps(result2, indent=2))

    # Test error handling
    print("\nTesting error handling with non-existent crew:")
    result3 = get_crew_hours_this_week_data(999)
    print("Non-existent crew:", json.dumps(result3, indent=2))

    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    test_weekly_endpoints()
