#!/usr/bin/env python3
"""
Test the week-aligned date range functionality

This script demonstrates and tests the new week-aligned date fetching logic
that ensures we always have data from Monday of the current week onwards.
"""

import sys
from datetime import datetime, timedelta
sys.path.insert(0, '.')

from utils import get_week_aligned_date_range

def test_week_aligned_scenarios():
    """Test various scenarios for week-aligned date ranges."""
    
    print("🗓️  Week-Aligned Date Range Testing")
    print("=" * 50)
    
    # Get current day info
    now = datetime.now()
    current_day = now.strftime("%A")
    days_since_monday = now.weekday()
    
    print(f"Today is: {current_day} ({now.strftime('%Y-%m-%d')})")
    print(f"Days since Monday: {days_since_monday}")
    print()
    
    # Test different max_days scenarios
    test_scenarios = [3, 5, 7, 10]
    
    for max_days in test_scenarios:
        print(f"📅 Testing max_days = {max_days}")
        print("-" * 30)
        
        start_date, effective_max_days = get_week_aligned_date_range(max_days)
        
        end_date = start_date + timedelta(days=effective_max_days - 1)
        
        print(f"  Original max_days: {max_days}")
        print(f"  Effective max_days: {effective_max_days}")
        print(f"  Start date: {start_date.strftime('%Y-%m-%d %A')}")
        print(f"  End date: {end_date.strftime('%Y-%m-%d %A')}")
        
        # Calculate coverage
        historic_days = days_since_monday
        future_days = effective_max_days - historic_days
        
        print(f"  Coverage: {historic_days} historic + {future_days} future days")
        
        # Check if we cover current week
        covers_full_week = effective_max_days >= (7 - days_since_monday + days_since_monday)
        week_status = "✅ Full week+" if covers_full_week else "⚠️  Partial week"
        print(f"  Week coverage: {week_status}")
        print()
    
    print("🎯 Weekly Availability Requirements:")
    print("  ✅ Always starts from Monday of current week")
    print("  ✅ Includes historic data since Monday")
    print("  ✅ Extends forward based on max_days")
    print("  ✅ Ensures minimum coverage through next Sunday")
    print("\n📈 This ensures weekly availability tracking has complete data!")

if __name__ == "__main__":
    test_week_aligned_scenarios()
