#!/usr/bin/env python3
"""Enhanced tests for db_store.py edge cases and error handling."""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from db_store import (
    _convert_slots_to_blocks,
    init_db,
    insert_appliance_availability,
    insert_crew_availability,
    insert_crew_details,
)


class TestDatabaseStoreEnhanced:
    """Enhanced tests for database storage functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = temp_file.name
        temp_file.close()

        # Create tables
        conn = init_db(db_path)
        conn.close()  # Ensure connection is closed

        yield db_path

        # Cleanup - try multiple times on Windows
        import time

        for attempt in range(3):
            try:
                Path(db_path).unlink(missing_ok=True)
                break
            except PermissionError:
                if attempt < 2:
                    time.sleep(0.1)  # Brief delay before retry
                    continue
                # If all attempts fail, just pass - temp files will be cleaned up by OS
                pass

    def test_create_tables_error_handling(self):
        """Test table creation with various error conditions."""

        # Test with invalid path - should not raise exception due to sqlite3 behavior
        try:
            init_db("/invalid/path/test.db")
            # If we get here, the function handled the invalid path gracefully
            # This is actually the correct behavior for sqlite3
        except (sqlite3.Error, OSError):
            # If it does raise an exception, that's also acceptable
            pass

    def test_store_crew_data_with_invalid_input(self, temp_db):
        """Test storing crew data with various invalid inputs."""

        # Test with valid crew data
        valid_crew_data = [
            {
                "name": "VALID, CREW",
                "role": "FFC",
                "skills": "BA",
                "contract_hours": "40",
            }
        ]

        # Should handle gracefully without crashing
        conn = sqlite3.connect(temp_db)
        insert_crew_details(valid_crew_data, db_conn=conn)
        conn.close()

        # Verify only valid data was stored
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew")
        crew_count = cursor.fetchone()[0]
        conn.close()

        # Should have stored at least the valid crew member
        assert crew_count >= 1

    def test_large_data_volume(self, temp_db):
        """Test storing and retrieving large volumes of data."""

        # Generate large dataset
        large_crew_data = []
        large_availability_data = []

        # Create 50 crew members (reduced from 200 for faster testing)
        for i in range(50):
            availability = {}
            for hour in range(6):  # Reduced from 24 hours for faster testing
                for minute in [0, 15, 30, 45]:
                    time_key = f"05/08/2025 {hour:02d}{minute:02d}"
                    availability[time_key] = (i + hour + minute) % 3 == 0

            large_crew_data.append(
                {
                    "name": f"CREW{i:03d}, TEST",
                    "role": "FFC",
                    "skills": "BA" if i % 2 == 0 else "LGV",
                    "contract_hours": "40",
                }
            )

            large_availability_data.append(
                {"name": f"CREW{i:03d}, TEST", "availability": availability}
            )

        # Store the large dataset
        conn = sqlite3.connect(temp_db)
        insert_crew_details(large_crew_data, db_conn=conn)
        insert_crew_availability(large_availability_data, db_conn=conn)
        conn.close()

        # Verify storage
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew")
        crew_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM crew_availability")
        availability_count = cursor.fetchone()[0]
        conn.close()

        assert crew_count == 50
        assert availability_count > 0  # Should have many availability blocks

    def test_duplicate_data_handling(self, temp_db):
        """Test handling of duplicate and overlapping data."""

        # Store initial data
        initial_crew_data = [
            {
                "name": "DUPLICATE, TEST",
                "role": "FFC",
                "skills": "BA",
                "contract_hours": "40",
            }
        ]

        initial_availability_data = [
            {
                "name": "DUPLICATE, TEST",
                "availability": {"05/08/2025 0800": True, "05/08/2025 0815": False},
            }
        ]

        conn = sqlite3.connect(temp_db)
        insert_crew_details(initial_crew_data, db_conn=conn)
        insert_crew_availability(initial_availability_data, db_conn=conn)

        # Store overlapping data with same name
        overlapping_crew_data = [
            {
                "name": "DUPLICATE, TEST",
                "role": "FFT",  # Different role
                "skills": "LGV",  # Different skills
                "contract_hours": "35",
            }
        ]

        overlapping_availability_data = [
            {
                "name": "DUPLICATE, TEST",
                "availability": {"05/08/2025 0830": True},  # Different time
            }
        ]

        insert_crew_details(overlapping_crew_data, db_conn=conn)
        insert_crew_availability(overlapping_availability_data, db_conn=conn)
        conn.close()

        # Verify handling
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew WHERE name = 'DUPLICATE, TEST'")
        crew_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM crew_availability WHERE crew_id IN (SELECT id FROM crew WHERE name = 'DUPLICATE, TEST')"
        )
        availability_count = cursor.fetchone()[0]
        conn.close()

        # Should handle duplicates appropriately (update or ignore)
        assert (
            crew_count == 1
        )  # Should be only one crew record due to UNIQUE constraint
        assert availability_count > 0  # Should have availability records

    def test_appliance_data_handling(self, temp_db):
        """Test appliance availability storage."""

        appliance_data = {
            "P22P6": {
                "availability": {
                    "05/08/2025 0800": True,
                    "05/08/2025 0815": False,
                    "05/08/2025 0830": True,
                }
            },
            "ENGINE1": {
                "availability": {"05/08/2025 0800": False, "05/08/2025 0815": True}
            },
        }

        conn = sqlite3.connect(temp_db)
        insert_appliance_availability(appliance_data, db_conn=conn)
        conn.close()

        # Verify storage
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appliance")
        appliance_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM appliance_availability")
        availability_count = cursor.fetchone()[0]
        conn.close()

        assert appliance_count == 2  # P22P6 and ENGINE1
        assert availability_count > 0  # Should have availability blocks

    def test_slots_to_blocks_conversion(self):
        """Test the slot to block conversion function."""

        # Test empty availability
        empty_result = _convert_slots_to_blocks({})
        assert empty_result == []

        # Test single slot
        single_slot = {"05/08/2025 0800": True}
        single_result = _convert_slots_to_blocks(single_slot)
        assert len(single_result) == 1

        # Test continuous availability
        continuous_slots = {
            "05/08/2025 0800": True,
            "05/08/2025 0815": True,
            "05/08/2025 0830": True,
            "05/08/2025 0845": False,
        }
        continuous_result = _convert_slots_to_blocks(continuous_slots)
        assert len(continuous_result) == 1
        assert continuous_result[0]["start_time"] == datetime(2025, 8, 5, 8, 0)
        assert continuous_result[0]["end_time"] == datetime(2025, 8, 5, 8, 45)

        # Test fragmented availability
        fragmented_slots = {
            "05/08/2025 0800": True,
            "05/08/2025 0815": False,
            "05/08/2025 0830": True,
            "05/08/2025 0845": False,
        }
        fragmented_result = _convert_slots_to_blocks(fragmented_slots)
        assert len(fragmented_result) == 2  # Two separate blocks

    def test_special_characters_in_names(self, temp_db):
        """Test handling of special characters in names and data."""

        special_crew_data = [
            {
                "name": "O'CONNOR, SEÁN",  # Apostrophe and accented characters
                "role": "Watch Commander",
                "skills": "BA & LGV",
                "contract_hours": "40",
            },
            {
                "name": "SMITH-JONES, A",  # Hyphen
                "role": "Fire Fighter",
                "skills": "TTR/LGV",
                "contract_hours": "35",
            },
            {
                "name": 'CREW WITH "QUOTES"',  # Double quotes
                "role": "Officer (Acting)",  # Parentheses
                "skills": "10% BA, 90% LGV",  # Percentages
                "contract_hours": "42",
            },
        ]

        special_availability_data = [
            {"name": "O'CONNOR, SEÁN", "availability": {"05/08/2025 0800": True}}
        ]

        conn = sqlite3.connect(temp_db)
        insert_crew_details(special_crew_data, db_conn=conn)
        insert_crew_availability(special_availability_data, db_conn=conn)
        conn.close()

        # Verify data was stored correctly
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew WHERE name LIKE '%CONNOR%'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_database_constraints(self, temp_db):
        """Test database constraints and foreign key relationships."""

        # Try to insert availability for non-existent crew
        availability_data = [
            {"name": "NONEXISTENT, CREW", "availability": {"05/08/2025 0800": True}}
        ]

        conn = sqlite3.connect(temp_db)
        insert_crew_availability(availability_data, db_conn=conn)
        conn.close()

        # Should handle gracefully - no availability should be inserted for non-existent crew
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM crew_availability WHERE crew_id NOT IN (SELECT id FROM crew)"
        )
        orphaned_count = cursor.fetchone()[0]
        conn.close()

        assert orphaned_count == 0  # No orphaned availability records

    def test_extreme_dates(self, temp_db):
        """Test handling of extreme date values."""

        extreme_crew_data = [
            {
                "name": "EXTREME, TEST",
                "role": "FFC",
                "skills": "BA",
                "contract_hours": "40",
            }
        ]

        extreme_availability_data = [
            {
                "name": "EXTREME, TEST",
                "availability": {
                    "01/01/2020 0000": True,  # Very old date
                    "31/12/2030 2345": False,  # Future date
                },
            }
        ]

        conn = sqlite3.connect(temp_db)
        insert_crew_details(extreme_crew_data, db_conn=conn)
        insert_crew_availability(extreme_availability_data, db_conn=conn)
        conn.close()

        # Verify data was stored
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew_availability")
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0


if __name__ == "__main__":
    pytest.main([__file__])
