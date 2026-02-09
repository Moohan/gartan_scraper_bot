import os
import sys

# Add the current directory to the path so we can import api_server
sys.path.append(os.getcwd())

from api_server import check_rules


def test_user_scenario():
    # Crew from user's report:
    # ID: 3, Name: GIBB, OL, Role: CC, Skills: BA ERD IC
    # ID: 2, Name: CASELY, CH, Role: FF, Skills: BA ERD
    # ID: 4540, Name: HAYES, JA, Role: FFD, Skills: BA
    # ID: 7, Name: SABA, JA, Role: FF, Skills: BA ERD

    # Crew members with their roles and skills
    crew_members = [
        {"name": "GIBB, OL", "role": "CC", "skills": "BA ERD IC"},
        {"name": "CASELY, CH", "role": "FF", "skills": "BA ERD"},
        {"name": "HAYES, JA", "role": "FFD", "skills": "BA"},
        {"name": "SABA, JA", "role": "FF", "skills": "BA ERD"},
    ]
    print(f"Checking rules for crew: {[c['name'] for c in crew_members]}")

    result = check_rules(crew_members)

    print("\n--- Results ---")
    print(f"Rules Pass: {result['rules_pass']}")
    print(f"Rules Detail: {result['rules']}")
    print(f"Skill Counts: {result['skill_counts']}")
    print(f"BA Non-TTR: {result['ba_non_ttr']}")

    if result["rules_pass"]:
        print("\nSUCCESS: The reported crew now passes the availability rules!")
    else:
        print("\nFAILURE: The reported crew still fails the availability rules.")


if __name__ == "__main__":
    test_user_scenario()
