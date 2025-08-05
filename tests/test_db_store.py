import os
import pytest
from db_store import (
    init_db,
    insert_crew_details,
    insert_crew_availability,
    insert_appliance_availability,
)


def test_db_schema():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    cursor = conn.cursor()
    # Check tables
    for table in ["crew", "crew_availability", "appliance", "appliance_availability"]:
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
        )
        assert cursor.fetchone(), f"Table {table} missing"
    conn.close()
    os.remove(db_path)


def test_insert_crew_details():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    crew_list = [
        {
            "name": "John Doe",
            "role": "Firefighter",
            "skills": "Skill",
            "contact": "123456789",
            "availability": {},
        }
    ]
    contact_map = {"John Doe": "123456789"}
    insert_crew_details(crew_list, contact_map, db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crew WHERE name='John Doe'")
    assert cursor.fetchone() is not None
    conn.close()
    os.remove(db_path)


def test_insert_empty_crew_details():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    contact_map = {}
    insert_crew_details([], contact_map, db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crew")
    assert cursor.fetchone() is None
    conn.close()
    os.remove(db_path)


def test_insert_empty_appliance_availability():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    insert_appliance_availability({}, db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appliance_availability")
    assert cursor.fetchone() is None
    conn.close()
    os.remove(db_path)


def test_insert_crew_missing_fields():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    crew_list = [{"name": "Jane"}]  # Missing role, skills, contact
    contact_map = {"Jane": ""}
    try:
        insert_crew_details(crew_list, contact_map, db_path)
    except Exception:
        pass  # Should not crash
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crew WHERE name='Jane'")
    assert cursor.fetchone() is not None
    conn.close()
    os.remove(db_path)


def test_insert_duplicate_crew():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    crew_list = [
        {
            "name": "Alex",
            "role": "Firefighter",
            "skills": "Skill",
            "contact": "555",
        }
    ]
    contact_map = {"Alex": "555"}
    insert_crew_details(crew_list, contact_map, db_path)
    # Insert duplicate
    insert_crew_details(crew_list, contact_map, db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM crew WHERE name='Alex'")
    count = cursor.fetchone()[0]
    assert count == 1  # Should not insert duplicate
    conn.close()
    os.remove(db_path)


def test_insert_crew_availability():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    crew_list = [
        {
            "name": "John Doe",
            "role": "Firefighter",
            "skills": "Skill",
            "contact": "123456789",
            "availability": {"2025-07-01 08:00": True},
        }
    ]
    # Insert crew details first
    contact_map = {"John Doe": "123456789"}
    from db_store import insert_crew_details

    insert_crew_details(crew_list, contact_map, db_path)
    insert_crew_availability(crew_list, db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crew_availability WHERE crew_id IS NOT NULL")
    assert cursor.fetchone() is not None
    conn.close()
    os.remove(db_path)


def test_insert_availability_for_nonexistent_crew():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    crew_list = [
        {
            "name": "Ghost",
            "role": "Firefighter",
            "skills": "Skill",
            "contact": "000",
            "availability": {"2025-07-01 08:00": True},
        }
    ]
    # Do not insert crew details
    try:
        insert_crew_availability(crew_list, db_path)
    except Exception:
        pass  # Should not crash
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crew_availability WHERE crew_id IS NOT NULL")
    assert cursor.fetchone() is None
    conn.close()
    os.remove(db_path)


def test_insert_appliance_availability():
    db_path = "test_gartan.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = init_db(db_path)
    appliance_obj = {"Engine 1": {"availability": {"2025-07-01 08:00": True}}}
    insert_appliance_availability(appliance_obj, db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM appliance_availability WHERE appliance_id IS NOT NULL"
    )
    assert cursor.fetchone() is not None
    conn.close()
    import time

    time.sleep(0.1)  # Ensure file is closed before delete
    os.remove(db_path)
