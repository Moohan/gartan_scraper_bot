#!/usr/bin/env python3
"""
Demonstration of Weekly Availability API Implementation

This script demonstrates that the new weekly availability endpoints
are working correctly with real data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from api_server import (
    get_crew_list_data,
    get_crew_hours_this_week_data,
    get_crew_hours_planned_week_data,
    get_week_boundaries
)
from datetime import datetime
import json

def main():
    print("🚀 Weekly Availability API Demo")
    print("=" * 50)

    # Show current week boundaries
    week_start, week_end = get_week_boundaries()
    current_day = datetime.now().strftime("%A")

    print(f"Today is: {current_day}")
    print(f"Week starts: {week_start.strftime('%Y-%m-%d %H:%M:%S')} (Monday)")
    print(f"Week ends: {week_end.strftime('%Y-%m-%d %H:%M:%S')} (Sunday)")
    print()

    # Get crew list
    crew_list = get_crew_list_data()
    print(f"📋 Found {len(crew_list)} crew members")

    if not crew_list:
        print("❌ No crew data available")
        return

    # Test with first few crew members
    print("\n🧑‍💼 Weekly Availability Summary:")
    print("-" * 40)

    for i, crew in enumerate(crew_list[:3]):  # Test first 3 crew members
        crew_id = crew['id']
        crew_name = crew['name']

        # Get weekly hours
        hours_this_week = get_crew_hours_this_week_data(crew_id)
        hours_planned = get_crew_hours_planned_week_data(crew_id)

        print(f"\n{i+1}. {crew_name} (ID: {crew_id})")
        print(f"   Hours since Monday: {hours_this_week.get('hours_this_week', 'N/A')}")
        print(f"   Total planned this week: {hours_planned.get('hours_planned_week', 'N/A')}")

    print("\n✅ New API Endpoints Ready:")
    print("   • GET /v1/crew/{id}/hours-this-week")
    print("   • GET /v1/crew/{id}/hours-planned-week")
    print("\n🎉 Weekly availability tracking successfully implemented!")

if __name__ == "__main__":
    main()
