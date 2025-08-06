#!/usr/bin/env python3
"""
Test script for scheduler functionality

Tests that the scheduler can run the scraper correctly
"""

import subprocess
import sys
import os
from datetime import datetime

def test_scheduler_import():
    """Test that scheduler can be imported"""
    try:
        import scheduler
        print("✅ Scheduler import successful")
        return True
    except ImportError as e:
        print(f"❌ Scheduler import failed: {e}")
        return False

def test_scraper_run():
    """Test that scraper can run with minimal parameters"""
    try:
        print("🧪 Testing scraper run...")
        result = subprocess.run([
            sys.executable, "run_bot.py", "--max-days", "1", "--cache-first"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ Scraper run successful")
            print(f"Output preview: {result.stdout[:200]}...")
            return True
        else:
            print(f"❌ Scraper failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Scraper timed out")
        return False
    except Exception as e:
        print(f"❌ Scraper test error: {e}")
        return False

def test_api_server_import():
    """Test that API server can be imported"""
    try:
        import api_server
        print("✅ API server import successful")
        return True
    except ImportError as e:
        print(f"❌ API server import failed: {e}")
        return False

def test_container_main_import():
    """Test that container main can be imported"""
    try:
        import container_main
        print("✅ Container main import successful") 
        return True
    except ImportError as e:
        print(f"❌ Container main import failed: {e}")
        return False

def main():
    """Run all container functionality tests"""
    print("🔧 Testing Container Functionality")
    print("=" * 50)
    
    tests = [
        test_scheduler_import,
        test_api_server_import, 
        test_container_main_import,
        test_scraper_run
    ]
    
    results = []
    for test in tests:
        print(f"\n🧪 Running {test.__name__}...")
        results.append(test())
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All container tests passed!")
        return True
    else:
        print("⚠️  Some tests failed - check Docker setup")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
