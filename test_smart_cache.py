#!/usr/bin/env python3
"""
Test smart cache functionality.
"""

import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from smart_cache import SmartCacheManager, get_cache_manager


def test_cache_manager_basic(tmp_path):
    """Test basic cache manager functionality."""
    cache_manager = SmartCacheManager(cache_dir=str(tmp_path))
    
    # Test cache miss
    assert not cache_manager.is_cache_valid("01/01/2025", 60)
    assert cache_manager.read_cache("01/01/2025") is None
    
    # Write cache
    test_content = "<html>Test content</html>"
    assert cache_manager.write_cache("01/01/2025", test_content)
    
    # Test cache hit
    assert cache_manager.is_cache_valid("01/01/2025", 60)
    assert cache_manager.read_cache("01/01/2025") == test_content


def test_cache_expiry(tmp_path):
    """Test cache expiry functionality."""
    cache_manager = SmartCacheManager(cache_dir=str(tmp_path))
    
    # Write cache
    test_content = "<html>Test content</html>"
    assert cache_manager.write_cache("01/01/2025", test_content)
    
    # Should be valid for 60 minutes
    assert cache_manager.is_cache_valid("01/01/2025", 60)
    
    # Should be expired for 0 minutes
    assert not cache_manager.is_cache_valid("01/01/2025", 0)


def test_cache_strategy():
    """Test cache strategy determination."""
    cache_manager = SmartCacheManager()
    
    # Test different date strategies
    today = datetime.now().strftime("%d/%m/%Y")
    future_date = (datetime.now() + timedelta(days=10)).strftime("%d/%m/%Y")
    past_date = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    
    assert cache_manager.get_cache_strategy(today, 15) == "cache-preferred"
    assert cache_manager.get_cache_strategy(future_date, 15) == "cache-first"
    assert cache_manager.get_cache_strategy(past_date, 15) == "cache-first"


def test_batch_cache_check(tmp_path):
    """Test batch cache checking."""
    # Create a unique subdirectory to avoid conflicts
    test_cache_dir = tmp_path / "batch_test"
    test_cache_dir.mkdir()
    
    cache_manager = SmartCacheManager(cache_dir=str(test_cache_dir))
    
    dates = ["01/01/2025", "02/01/2025", "03/01/2025"]
    
    # All should be invalid initially
    results = cache_manager.batch_cache_check(dates, 60)
    print(f"Initial results: {results}")  # Debug output
    assert all(not valid for valid in results.values())
    
    # Write cache for one date
    cache_manager.write_cache("02/01/2025", "<html>Test</html>")
    
    # Check batch again
    results = cache_manager.batch_cache_check(dates, 60)
    print(f"After cache write: {results}")  # Debug output
    assert not results["01/01/2025"]
    assert results["02/01/2025"]
    assert not results["03/01/2025"]


def test_cache_cleanup(tmp_path):
    """Test cache cleanup functionality."""
    cache_manager = SmartCacheManager(cache_dir=str(tmp_path))
    
    # Create some cache files
    cache_manager.write_cache("01/01/2025", "<html>Test 1</html>")
    cache_manager.write_cache("02/01/2025", "<html>Test 2</html>")
    
    # Artificially age one file
    import os
    old_file = cache_manager.get_cache_file_path("01/01/2025")
    old_time = time.time() - (35 * 24 * 60 * 60)  # 35 days ago
    os.utime(old_file, (old_time, old_time))
    
    # Cleanup should remove the old file
    removed_count = cache_manager.cleanup_expired_cache(max_age_days=30)
    assert removed_count == 1
    
    # Check that only new file remains
    assert not cache_manager.is_cache_valid("01/01/2025", 60)
    assert cache_manager.is_cache_valid("02/01/2025", 60)


def test_cache_stats(tmp_path):
    """Test cache statistics."""
    # Use isolated directory
    stats_cache_dir = tmp_path / "stats_test"
    stats_cache_dir.mkdir()
    
    cache_manager = SmartCacheManager(cache_dir=str(stats_cache_dir))
    
    # Initially empty
    stats = cache_manager.get_cache_stats()
    assert stats["total_files"] == 0
    assert stats["total_size"] == 0
    
    # Add some cache files
    cache_manager.write_cache("01/01/2025", "<html>Test content</html>")
    cache_manager.write_cache("02/01/2025", "<html>More test content</html>")
    
    # Check updated stats
    stats = cache_manager.get_cache_stats()
    assert stats["total_files"] == 2
    assert stats["total_size"] > 0


def test_global_cache_manager():
    """Test global cache manager instance."""
    manager1 = get_cache_manager()
    manager2 = get_cache_manager()
    assert manager1 is manager2
    
    # Different cache dir should create new manager
    manager3 = get_cache_manager("/tmp")
    assert manager1 is not manager3


if __name__ == "__main__":
    print("Testing smart cache manager...")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_cache_manager_basic(Path(tmp_dir))
        print("✅ Basic cache manager test passed")
        
        test_cache_expiry(Path(tmp_dir))
        print("✅ Cache expiry test passed")
        
        test_cache_strategy()
        print("✅ Cache strategy test passed")
        
        test_batch_cache_check(Path(tmp_dir))
        print("✅ Batch cache check test passed")
        
        test_cache_cleanup(Path(tmp_dir))
        print("✅ Cache cleanup test passed")
        
        test_cache_stats(Path(tmp_dir))
        print("✅ Cache stats test passed")
        
        test_global_cache_manager()
        print("✅ Global cache manager test passed")
    
    print("\n🚀 All smart cache tests passed!")
