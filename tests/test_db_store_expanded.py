import os
import pytest
import sqlite3
from db_store import (
    init_db,
    insert_crew_details,
    insert_crew_availability,
    insert_appliance_availability,
)


def test_db_schema_creation(tmp_path):
    db_path = tmp_path / "test_gartan.db"
    conn = init_db(str(db_path))
    cursor = conn.cursor()
    for table in ["crew", "crew_availability", "appliance", "appliance_availability"]:
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
        )
        assert cursor.fetchone(), f"Table {table} missing"
    conn.close()


def test_insert_crew_details_and_availability(tmp_path):
    db_path = tmp_path / "test_gartan.db"
    conn = init_db(str(db_path))
    crew_list = [
        {
            "name": "John Doe",
            "role": "Firefighter",
            "skills": "Skill",
            "contact": "123456789",
            "availability": {"05/08/2025 0800": True},
        }
    ]
    contact_map = {"John Doe": "123456789"}
    insert_crew_details(crew_list, contact_map, conn)
    insert_crew_availability(crew_list, conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crew WHERE name='John Doe'")
    assert cursor.fetchone() is not None
    cursor.execute("SELECT * FROM crew_availability WHERE crew_id IS NOT NULL")
    assert cursor.fetchone() is not None
    conn.close()


def test_insert_appliance_availability(tmp_path):
    db_path = tmp_path / "test_gartan.db"
    conn = init_db(str(db_path))
    appliance_obj = {"Engine 1": {"availability": {"05/08/2025 0800": True}}}
    insert_appliance_availability(appliance_obj, conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appliance WHERE name='Engine 1'")
    assert cursor.fetchone() is not None
    cursor.execute(
        "SELECT * FROM appliance_availability WHERE appliance_id IS NOT NULL"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_insert_multiple_crew_and_appliance(tmp_path):
    db_path = tmp_path / "test_gartan.db"
    conn = init_db(str(db_path))
    crew_list = [
        {
            "name": "John Doe",
            "role": "Firefighter",
            "skills": "Skill",
            "contact": "123456789",
            "availability": {"05/08/2025 0800": True},
        },
        {
            "name": "Jane Smith",
            "role": "Officer",
            "skills": "First Aid",
            "contact": "987654321",
            "availability": {"05/08/2025 0815": False},
        },
    ]
    contact_map = {"John Doe": "123456789", "Jane Smith": "987654321"}
    insert_crew_details(crew_list, contact_map, conn)
    insert_crew_availability(crew_list, conn)
    appliance_obj = {
        "Engine 1": {"availability": {"05/08/2025 0800": True}},
        "Engine 2": {"availability": {"05/08/2025 0815": False}},
    }
    insert_appliance_availability(appliance_obj, conn)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM crew")
    assert cursor.fetchone()[0] == 2
    cursor.execute("SELECT COUNT(*) FROM appliance")
    assert cursor.fetchone()[0] == 2
    conn.close()


def test_insert_edge_case_data(tmp_path):
    db_path = tmp_path / "test_gartan.db"
    conn = init_db(str(db_path))
    crew_list = [
        {
            "name": "A" * 100,
            "role": "Firefighter",
            "skills": "Skill",
            "contact": "!@#$%^&*()",
            "availability": {"05/08/2025 0800": True},
        },
    ]
    contact_map = {"A" * 100: "!@#$%^&*()"}
    insert_crew_details(crew_list, contact_map, conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crew WHERE name=?", ("A" * 100,))
    assert cursor.fetchone() is not None
    conn.close()


def test_transaction_rollback_on_error(tmp_path):
    db_path = tmp_path / "test_gartan.db"
    conn = init_db(str(db_path))
    crew_list = [
        {
            "name": "Rollback",
            "role": "Firefighter",
            "skills": "Skill",
            "contact": "123",
            "availability": {"05/08/2025 0800": True},
        },
    ]
    contact_map = {"Rollback": "123"}
    insert_crew_details(crew_list, contact_map, conn)
    # Simulate error by passing invalid appliance_obj
    try:
        insert_appliance_availability(None, conn)  # type: ignore
    except Exception:
        pass
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crew WHERE name='Rollback'")
    assert cursor.fetchone() is not None  # Crew insert should persist
    conn.close()
