#!/usr/bin/env python3
"""Demonstrate cache strategy for week-aligned fetching"""

import sys
sys.path.insert(0, '.')

from utils import get_week_aligned_date_range
from config import config
from datetime import datetime, timedelta

def main():
    print("Cache Strategy for Week-Aligned Fetching:")
    print("=" * 50)
    
    today = datetime.now()
    start_date, effective_max_days = get_week_aligned_date_range(3)
    
    print(f"Today: {today.strftime('%A, %Y-%m-%d')}")
    print(f"Start: {start_date.strftime('%A, %Y-%m-%d')}")
    print(f"Days to fetch: {effective_max_days}")
    print()
    
    print("Date          | Days from Today | Cache Strategy")
    print("-" * 55)
    
    for day_offset in range(effective_max_days):
        current_date = start_date + timedelta(days=day_offset)
        days_from_today = (current_date.date() - today.date()).days
        cache_minutes = config.get_cache_minutes(days_from_today)
        
        if cache_minutes == -1:
            strategy = "Infinite (historic)"
        else:
            strategy = f"{cache_minutes} minutes"
        
        date_str = current_date.strftime("%m/%d (%a)")
        print(f"{date_str:<13} | {days_from_today:>15} | {strategy}")
    
    print()
    print("✅ Historic data will never be refetched!")
    print("⏰ Current/future data uses appropriate expiry times")

if __name__ == "__main__":
    main()
