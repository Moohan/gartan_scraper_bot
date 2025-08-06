#!/usr/bin/env python3
"""
Docker Deployment Validation Script

Validates that the containerized deployment is working correctly
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

API_BASE = "http://localhost:5000"
TIMEOUT = 10


def test_health_endpoint() -> bool:
    """Test the health check endpoint"""
    try:
        print("🏥 Testing health endpoint...")
        response = requests.get(f"{API_BASE}/health", timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Database: {data['database']}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_crew_endpoints() -> bool:
    """Test crew-related endpoints"""
    try:
        print("\n👥 Testing crew endpoints...")
        
        # Test crew list
        response = requests.get(f"{API_BASE}/v1/crew", timeout=TIMEOUT)
        if response.status_code != 200:
            print(f"❌ Crew list failed with status {response.status_code}")
            return False
        
        crew_list = response.json()
        if not isinstance(crew_list, list) or len(crew_list) == 0:
            print("❌ Crew list is empty or invalid")
            return False
        
        print(f"✅ Crew list: {len(crew_list)} members")
        
        # Test crew availability for first member
        first_crew = crew_list[0]
        crew_id = first_crew["id"]
        crew_name = first_crew["name"]
        
        # Test availability
        response = requests.get(f"{API_BASE}/v1/crew/{crew_id}/available", timeout=TIMEOUT)
        if response.status_code != 200:
            print(f"❌ Crew availability failed with status {response.status_code}")
            return False
        
        available = response.json()
        print(f"✅ {crew_name} available: {available}")
        
        # Test duration
        response = requests.get(f"{API_BASE}/v1/crew/{crew_id}/duration", timeout=TIMEOUT)
        if response.status_code != 200:
            print(f"❌ Crew duration failed with status {response.status_code}")
            return False
        
        duration = response.json()
        print(f"✅ {crew_name} duration: {duration}")
        
        return True
        
    except Exception as e:
        print(f"❌ Crew endpoints error: {e}")
        return False


def test_appliance_endpoints() -> bool:
    """Test appliance-related endpoints"""
    try:
        print("\n🚒 Testing appliance endpoints...")
        
        # Test P22P6 (known appliance)
        appliance_name = "P22P6"
        
        # Test availability
        response = requests.get(f"{API_BASE}/v1/appliances/{appliance_name}/available", timeout=TIMEOUT)
        if response.status_code != 200:
            print(f"❌ Appliance availability failed with status {response.status_code}")
            return False
        
        available = response.json()
        print(f"✅ {appliance_name} available: {available}")
        
        # Test duration
        response = requests.get(f"{API_BASE}/v1/appliances/{appliance_name}/duration", timeout=TIMEOUT)
        if response.status_code != 200:
            print(f"❌ Appliance duration failed with status {response.status_code}")
            return False
        
        duration = response.json()
        print(f"✅ {appliance_name} duration: {duration}")
        
        return True
        
    except Exception as e:
        print(f"❌ Appliance endpoints error: {e}")
        return False


def test_error_handling() -> bool:
    """Test error handling for invalid requests"""
    try:
        print("\n🚨 Testing error handling...")
        
        # Test invalid crew ID
        response = requests.get(f"{API_BASE}/v1/crew/999/available", timeout=TIMEOUT)
        if response.status_code != 404:
            print(f"❌ Invalid crew ID should return 404, got {response.status_code}")
            return False
        
        print("✅ Invalid crew ID returns 404")
        
        # Test invalid appliance name
        response = requests.get(f"{API_BASE}/v1/appliances/INVALID/available", timeout=TIMEOUT)
        if response.status_code != 404:
            print(f"❌ Invalid appliance should return 404, got {response.status_code}")
            return False
        
        print("✅ Invalid appliance returns 404")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test error: {e}")
        return False


def wait_for_service(max_wait: int = 60) -> bool:
    """Wait for the service to become available"""
    print(f"⏳ Waiting for service to start (max {max_wait}s)...")
    
    for i in range(max_wait):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Service is ready after {i+1}s")
                return True
        except:
            pass
        
        if i % 10 == 0 and i > 0:
            print(f"   Still waiting... ({i}s/{max_wait}s)")
        
        time.sleep(1)
    
    print(f"❌ Service not ready after {max_wait}s")
    return False


def main():
    """Run all deployment validation tests"""
    print("🐳 Docker Deployment Validation")
    print("=" * 50)
    
    # Wait for service to start
    if not wait_for_service():
        print("\n❌ Service is not available - check Docker deployment")
        return False
    
    # Run tests
    tests = [
        test_health_endpoint,
        test_crew_endpoints,
        test_appliance_endpoints,
        test_error_handling,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 50)
    print(f"📊 Validation Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 Docker deployment validation successful!")
        print("\n📋 Service is ready:")
        print(f"   Health: {API_BASE}/health")
        print(f"   API:    {API_BASE}/v1/crew")
        return True
    else:
        print("❌ Some validation tests failed")
        print("\n🔧 Troubleshooting:")
        print("   1. Check container status: docker-compose ps")
        print("   2. Check logs: docker-compose logs -f")
        print("   3. Verify database: check health endpoint")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
