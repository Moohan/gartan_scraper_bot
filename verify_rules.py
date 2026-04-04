import os
import sys

# Add the current directory to the path so we can import api_server
sys.path.append(os.getcwd())

from api_server import check_rules, get_db


def test_user_scenario():
    # Crew from user's report:
    # ID: 3, Name: GIBB, OL, Role: CC, Skills: BA ERD IC
    # ID: 2, Name: CASELY, CH, Role: FF, Skills: BA ERD
    # ID: 4540, Name: HAYES, JA, Role: FFD, Skills: BA
    # ID: 7, Name: SABA, JA, Role: FF, Skills: BA ERD

    available_ids = [3, 2, 4540, 7]
    print(f"Checking rules for crew IDs: {available_ids}")

    with get_db() as conn:
        # Fetch all crew and filter in Python to satisfy strict CI security scanners
        # for dynamic IN clauses, suitable for this small dataset.
        all_crew = conn.execute("SELECT id, role, skills FROM crew").fetchall()
        available_crew = [r for r in all_crew if r["id"] in available_ids]

    result = check_rules(available_crew)

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
