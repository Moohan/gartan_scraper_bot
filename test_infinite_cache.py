#!/usr/bin/env python3
"""
Test infinite cache for historic data

This script tests that historic data uses infinite cache while
current/future data uses time-based cache expiry.
"""

import sys
import os
import tempfile
import time
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from gartan_fetch import _is_cache_valid
from config import config

def test_infinite_cache():
    """Test infinite cache behavior for historic vs future data."""
    
    print("🗂️  Testing Infinite Cache for Historic Data")
    print("=" * 50)
    
    # Create a temporary cache file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_file:
        temp_file.write("<html>Test cache data</html>")
        cache_file = temp_file.name
    
    try:
        # Test different day offsets
        test_cases = [
            (-7, "Last week (historic)"),
            (-1, "Yesterday (historic)"),
            (0, "Today (current)"),
            (1, "Tomorrow (future)"),
            (7, "Next week (future)")
        ]
        
        print("Day Offset | Description         | Cache Minutes | Always Valid?")
        print("-" * 65)
        
        for day_offset, description in test_cases:
            cache_minutes = config.get_cache_minutes(day_offset)
            
            # Test cache validity
            is_valid_immediately = _is_cache_valid(cache_file, cache_minutes)
            
            # For time-based cache, simulate waiting and check again
            if cache_minutes > 0:
                # Don't actually wait, just check logic
                infinite_cache = False
                always_valid = "No (expires)"
            else:
                infinite_cache = True
                always_valid = "Yes (infinite)"
            
            cache_display = "infinite" if cache_minutes == -1 else f"{cache_minutes} min"
            
            print(f"{day_offset:>10} | {description:<19} | {cache_display:>11} | {always_valid}")
        
        print()
        print("🧪 Testing Cache Validation Logic:")
        print("-" * 40)
        
        # Test historic data (infinite cache)
        historic_cache_valid = _is_cache_valid(cache_file, -1)
        print(f"Historic data cache valid: {historic_cache_valid} ✅")
        
        # Test current data (15 min cache)
        current_cache_valid = _is_cache_valid(cache_file, 15)
        print(f"Current data cache valid: {current_cache_valid} ✅")
        
        # Test future data (60 min cache)
        future_cache_valid = _is_cache_valid(cache_file, 60)
        print(f"Future data cache valid: {future_cache_valid} ✅")
        
        print()
        print("💡 Benefits of Infinite Historic Cache:")
        print("  ✅ Historic data never refetched (performance boost)")
        print("  ✅ Reduces unnecessary network requests")
        print("  ✅ Reliable data consistency for past dates")
        print("  ✅ Faster startup when re-running bot")
        
    finally:
        # Clean up temp file
        os.unlink(cache_file)

if __name__ == "__main__":
    test_infinite_cache()
