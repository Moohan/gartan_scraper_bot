#!/usr/bin/env python3
"""
Automated API Validation Script

Generates validation questions by querying the API and presents them
in a format that can be quickly validated against real-world data.
"""

import os
import subprocess
import sys
import time
from datetime import datetime

import requests

# Configuration - can be overridden via environment variable
API_BASE = os.getenv("VALIDATION_API_BASE", "http://localhost:5000")  # Local by default


def get_api_response(endpoint):
    """Get API response with error handling."""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def ensure_local_api_running():
    """Ensure local API server is running, start it if needed."""
    try:
        # Quick health check
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            print("✅ Local API server is running")
            return True
    except requests.exceptions.RequestException:
        pass

    print("🚀 Starting local API server...")

    # Start API server in background
    try:
        subprocess.Popen(
            ["python", "api_server.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for server to start
        for _ in range(10):  # Try for 10 seconds
            time.sleep(1)
            try:
                response = requests.get(f"{API_BASE}/health", timeout=1)
                if response.status_code == 200:
                    print("✅ Local API server started successfully")
                    return True
            except requests.exceptions.RequestException:
                continue

        print("❌ Failed to start local API server")
        return False

    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        return False


def print_header():
    """Print validation header."""
    current_time = datetime.now()
    print("=" * 60)
    print("🤖 AUTOMATED API VALIDATION")
    print("=" * 60)
    print(f"📅 Generated at: {current_time.strftime('%H:%M on %d/%m/%Y')}")
    print(f"🌐 API Endpoint: {API_BASE}")
    if "localhost" in API_BASE:
        print("🏠 Running LOCAL validation (faster iteration)")
    else:
        print("🌍 Running REMOTE validation (production RPi)")
    print("=" * 60)
    return current_time


def collect_api_data():
    """Collect all API data needed for validation."""
    print("\n📊 COLLECTING API DATA...")

    crew_list = get_api_response("/v1/crew")
    appliance_status = get_api_response("/v1/appliances/P22P6/available")
    appliance_duration = get_api_response("/v1/appliances/P22P6/duration")

    crew_availability = {}
    crew_durations = {}
    for crew in crew_list:
        if isinstance(crew, dict) and "id" in crew:
            crew_id = crew["id"]
            availability = get_api_response(f"/v1/crew/{crew_id}/available")
            duration = get_api_response(f"/v1/crew/{crew_id}/duration")
            crew_availability[crew_id] = availability
            crew_durations[crew_id] = duration

    print("✅ API data collected successfully!")

    return {
        "crew_list": crew_list,
        "appliance_status": appliance_status,
        "appliance_duration": appliance_duration,
        "crew_availability": crew_availability,
        "crew_durations": crew_durations,
    }


def print_crew_questions(data, current_time):
    """Print crew availability questions."""
    print(f"\n🧑‍🚒 CREW AVAILABILITY (Current Time: {current_time.strftime('%H:%M')})")
    print("-" * 40)

    for crew in sorted(data["crew_list"], key=lambda x: x.get("id", 0)):
        if isinstance(crew, dict) and "id" in crew:
            crew_id = crew["id"]
            name = crew.get("display_name", crew.get("name", "Unknown"))
            api_available = data["crew_availability"].get(crew_id, False)

            status = "✅ YES" if api_available else "❌ NO"
            print(f"  {name:<15} | API: {status:<6} | Real: YES/NO ____")


def print_appliance_questions(data):
    """Print appliance availability questions."""
    print("\n🚒 APPLIANCE AVAILABILITY")
    print("-" * 40)
    api_appliance = data["appliance_status"]
    status = "✅ YES" if api_appliance else "❌ NO"
    print(f"  P22P6 Available    | API: {status:<6} | Real: YES/NO ____")


def print_duration_questions(data):
    """Print duration questions."""
    print("\n⏱️  DURATION QUESTIONS")
    print("-" * 40)

    # Find available crew for duration questions
    available_crew = []
    for crew in data["crew_list"]:
        if isinstance(crew, dict) and "id" in crew:
            crew_id = crew["id"]
            if data["crew_availability"].get(crew_id, False):
                name = crew.get("display_name", crew.get("name", "Unknown"))
                api_duration = data["crew_durations"].get(crew_id, "N/A")
                available_crew.append((name, api_duration))

    if available_crew:
        print(
            "  (For currently available crew - how long until they become unavailable?)"
        )
        for name, api_duration in available_crew[:3]:  # Limit to first 3 for brevity
            print(f"  {name:<15} | API: {api_duration:<8} | Real: ____:____ (HH:MM)")

    # Appliance duration
    api_appliance = data["appliance_status"]
    if api_appliance:
        api_appliance_duration = data["appliance_duration"]
        print(
            f"\n  P22P6 Duration     | API: {api_appliance_duration:<8} | Real: ____:____ (HH:MM)"
        )


def print_business_rules_questions(data):
    """Print business rules validation questions."""
    print("\n🔧 BUSINESS RULES CHECK")
    print("-" * 40)

    # Count available crew by skills
    available_with_skills = []
    for crew in data["crew_list"]:
        if isinstance(crew, dict) and "id" in crew:
            crew_id = crew["id"]
            if data["crew_availability"].get(crew_id, False):
                name = crew.get("display_name", crew.get("name", "Unknown"))
                skills = crew.get("skills", "")
                role = crew.get("role", "")
                available_with_skills.append((name, skills, role))

    total_available = len(available_with_skills)
    ttr_available = any("TTR" in skills for _, skills, _ in available_with_skills)
    lgv_available = any("LGV" in skills for _, skills, _ in available_with_skills)
    ba_count = sum(
        1
        for _, skills, _ in available_with_skills
        if "BA" in skills and "TTR" not in skills
    )
    ffc_plus_ba = any(
        "BA" in skills and "TTR" not in skills and role in ["WC", "CC", "FFC"]
        for _, skills, role in available_with_skills
    )

    should_be_available = (
        total_available >= 4
        and ttr_available
        and lgv_available
        and ba_count >= 2
        and ffc_plus_ba
    )

    # Format status
    def format_status(condition):
        return "✅ YES" if condition else "❌ NO"

    print(
        f"  Total Crew ≥4      | API: {format_status(total_available >= 4):<6} | Real: YES/NO ____ (Count: ____)"
    )
    print(
        f"  TTR Skill Present  | API: {format_status(ttr_available):<6} | Real: YES/NO ____"
    )
    print(
        f"  LGV Skill Present  | API: {format_status(lgv_available):<6} | Real: YES/NO ____"
    )
    print(
        f"  ≥2 BA (non-TTR)    | API: {format_status(ba_count >= 2):<6} | Real: YES/NO ____ (Count: ____)"
    )
    print(
        f"  ≥1 FFC+ with BA    | API: {format_status(ffc_plus_ba):<6} | Real: YES/NO ____"
    )

    print("\n🚨 OVERALL P22P6 DECISION")
    print("-" * 40)
    api_appliance = data["appliance_status"]
    print(
        f"  Should Operate     | API: {format_status(should_be_available):<6} | Real: YES/NO ____"
    )
    print(
        f"  Actually Available | API: {format_status(api_appliance):<6} | Real: YES/NO ____"
    )

    # Summary information
    print("\n📋 API SUMMARY")
    print("-" * 40)
    print(f"  Available Crew: {total_available}")
    all_skills = set()
    all_roles = set()
    for _, skills, role in available_with_skills:
        all_skills.update(skill for skill in skills.split() if skill)
        if role:
            all_roles.add(role)

    print(f"  Skills Present: {', '.join(sorted(all_skills))}")
    print(f"  Roles Present: {', '.join(sorted(all_roles))}")


def generate_validation_questions():
    """Generate automated validation questions."""
    # Ensure local API is running (only for localhost)
    if "localhost" in API_BASE:
        if not ensure_local_api_running():
            print("💥 Cannot continue without API server running")
            return False

    current_time = print_header()

    data = collect_api_data()

    # Check if we got valid data
    if "error" in data.get("crew_list", {}):
        print(f"❌ Failed to collect crew data: {data['crew_list']['error']}")
        return False

    # Generate questions
    print("\n" + "=" * 60)
    print("❓ VALIDATION QUESTIONS")
    print("=" * 60)
    print("📝 Please answer with the REAL WORLD data you can see:")
    print("   • YES/NO for availability questions")
    print("   • TIME (HH:MM) for duration questions")
    print("   • Fill in START TIME and END TIME")
    print("=" * 60)

    print("\n⏰ VALIDATION START TIME: ____:____")

    print_crew_questions(data, current_time)
    print_appliance_questions(data)
    print_duration_questions(data)
    print_business_rules_questions(data)

    print("\n⏰ VALIDATION END TIME: ____:____")
    print("=" * 60)

    # Show validation mode reminder
    if "localhost" in API_BASE:
        print("\n💡 TIP: To test against RPi, set environment variable:")
        print("   VALIDATION_API_BASE=http://192.168.86.66:5000")

    return True


if __name__ == "__main__":
    generate_validation_questions()

if __name__ == "__main__":
    try:
        success = generate_validation_questions()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Validation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Error during validation: {e}")
        sys.exit(1)
