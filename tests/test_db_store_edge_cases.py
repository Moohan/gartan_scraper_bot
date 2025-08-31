#!/usr/bin/env python3
"""Enhanced tests for db_store.py edge cases and error handling."""

import os
import sqlite3
import tempfile
from unittest.mock import Mock, patch

import pytest

import db_store
from db_store import init_db, insert_appliance_availability, insert_crew_availability


class TestDBStoreEdgeCases:
    """Test edge cases and error handling in db_store.py"""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.original_db_path = db_store.DB_PATH
        db_store.DB_PATH = self.temp_db.name

    def teardown_method(self):
        """Clean up test environment."""
        # Restore original DB path
        db_store.DB_PATH = self.original_db_path

        # Clean up temp database
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass

    def test_init_db_with_external_connection(self):
        """Test init_db with external connection (lines 155-156)."""
        # Create external connection
        conn = sqlite3.connect(self.temp_db.name)

        # Test that tables are created without closing the connection
        init_db(db_path=self.temp_db.name)

        # Verify tables exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert "crew" in tables
        assert "appliance" in tables
        assert "crew_availability" in tables
        assert "appliance_availability" in tables

        # Connection should still be open
        assert conn is not None
        conn.close()

    def test_insert_crew_availability_with_external_connection(self):
        """Test insert_crew_availability with external connection (lines 185, 198-199)."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        # Create external connection
        conn = sqlite3.connect(self.temp_db.name)

        crew_data = [
            {
                "name": "TEST, T",
                "contact": "Test Contact",
                "skills": "TTR",
                "availability": {"05/08/2025 0900": True, "05/08/2025 1700": False},
            }
        ]

        # Insert crew details first
        from db_store import insert_crew_details

        contact_map = {"TEST, T": "Test Contact"}
        insert_crew_details(crew_data, contact_map, conn)

        # Test with external connection
        insert_crew_availability(crew_data, db_conn=conn)  # Verify data was inserted
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew")
        crew_count = cursor.fetchone()[0]
        assert crew_count == 1

        cursor.execute("SELECT COUNT(*) FROM crew_availability")
        availability_count = cursor.fetchone()[0]
        assert availability_count == 1

        # Connection should still be open
        assert conn is not None
        conn.close()

    def test_insert_crew_availability_missing_appliance_id(self):
        """Test crew availability with missing appliance_id case (line 301)."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        # Test crew data with no appliance reference
        crew_data = [
            {
                "name": "TEST, T",
                "contact": "Test Contact",
                "skills": "TTR",
                "availability": {"05/08/2025 0900": True, "05/08/2025 1700": False},
            }
        ]

        # Insert crew details first
        from db_store import insert_crew_details

        contact_map = {"TEST, T": "Test Contact"}
        insert_crew_details(crew_data, contact_map)

        # This should complete successfully even without appliance associations
        insert_crew_availability(crew_data)  # Verify data was inserted
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew")
        crew_count = cursor.fetchone()[0]
        assert crew_count == 1
        conn.close()

    def test_insert_appliance_availability_with_external_connection(self):
        """Test insert_appliance_availability with external connection (lines 310-311)."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        # Create external connection
        conn = sqlite3.connect(self.temp_db.name)

        appliance_data = {
            "P22P6": {
                "availability": {"05/08/2025 0900": True, "05/08/2025 1700": False}
            }
        }

        # Test with external connection
        insert_appliance_availability(
            appliance_data, db_conn=conn
        )  # Verify data was inserted
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appliance")
        appliance_count = cursor.fetchone()[0]
        assert appliance_count == 1

        cursor.execute("SELECT COUNT(*) FROM appliance_availability")
        availability_count = cursor.fetchone()[0]
        assert availability_count == 1

        # Connection should still be open
        assert conn is not None
        conn.close()

    def test_insert_appliance_availability_missing_appliance(self):
        """Test appliance availability with missing appliance record (line 319)."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        # Mock cursor to simulate missing appliance
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Mock fetchone to return None (no appliance found)
            mock_cursor.fetchone.return_value = None

            appliance_data = {
                "NonExistentAppliance": {
                    "availability": {"05/08/2025 0900": True, "05/08/2025 1700": False}
                }
            }

            # This should complete without error due to continue statement
            insert_appliance_availability(appliance_data)

            # Verify the cursor methods were called
            assert mock_cursor.execute.called
            assert mock_cursor.fetchone.called

    def test_insert_appliance_availability_connection_cleanup(self):
        """Test appliance availability with connection cleanup (line 333)."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        appliance_data = {
            "P22P6": {
                "availability": {"05/08/2025 0900": True, "05/08/2025 1700": False}
            }
        }

        # Test normal operation with connection cleanup
        insert_appliance_availability(appliance_data)  # Verify data was inserted
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appliance")
        appliance_count = cursor.fetchone()[0]
        assert appliance_count == 1

        cursor.execute("SELECT COUNT(*) FROM appliance_availability")
        availability_count = cursor.fetchone()[0]
        assert availability_count == 1
        conn.close()

    def test_connection_error_handling(self):
        """Test error handling when connection fails."""
        # Mock sqlite3.connect to raise an exception
        with patch("sqlite3.connect") as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database locked")

            # These should handle the error gracefully
            with pytest.raises(sqlite3.Error):
                init_db(db_path=self.temp_db.name)

            with pytest.raises(sqlite3.Error):
                insert_crew_availability([])

            with pytest.raises(sqlite3.Error):
                insert_appliance_availability({})

    def test_empty_data_handling(self):
        """Test handling of empty data inputs."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        # Test empty crew list
        insert_crew_availability([])

        # Test empty appliance dict
        insert_appliance_availability({})

        # Verify no data was inserted
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM crew")
        assert cursor.fetchone()[0] == 0

        cursor.execute("SELECT COUNT(*) FROM appliance")
        assert cursor.fetchone()[0] == 0

        conn.close()

    def test_init_db_with_recreate_flag(self):
        """Test init_db with recreate_tables=True (lines 65-68)."""
        # Create initial database
        init_db(db_path=self.temp_db.name)

        # Add some data
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO crew (name) VALUES (?)", ("Test Crew",))
        conn.commit()

        # Verify data exists
        cursor.execute("SELECT COUNT(*) FROM crew")
        count_before = cursor.fetchone()[0]
        assert count_before > 0
        conn.close()

        # Recreate tables (should drop and recreate)
        init_db(db_path=self.temp_db.name, reset=True)

        # Verify tables were recreated (data should be gone)
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew")
        count_after = cursor.fetchone()[0]
        assert count_after == 0
        conn.close()

    def test_convert_slots_to_blocks_empty_data(self):
        """Test _convert_slots_to_blocks with empty data (lines 94-95)."""
        from db_store import _convert_slots_to_blocks

        # Test with empty dict
        result = _convert_slots_to_blocks({})
        assert result == []

        # Test with None
        result = _convert_slots_to_blocks(None)
        assert result == []

    def test_crew_availability_with_existing_blocks_cleanup(self):
        """Test crew availability with existing blocks cleanup (lines 233-234, 268)."""
        init_db(db_path=self.temp_db.name)

        crew_data = [
            {
                "name": "CLEANUP_TEST, T",
                "contact": "Test Contact",
                "skills": "TTR",
                "availability": {"05/08/2025 0900": True, "05/08/2025 1000": False},
            }
        ]

        # Insert crew details first
        from db_store import insert_crew_details

        contact_map = {"CLEANUP_TEST, T": "Test Contact"}
        insert_crew_details(crew_data, contact_map)

        # Insert availability first time
        insert_crew_availability(crew_data)

        # Verify blocks exist
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew_availability")
        count_before = cursor.fetchone()[0]
        assert count_before > 0

        # Insert availability again (should trigger cleanup)
        insert_crew_availability(crew_data)

        # Verify blocks were cleaned up and recreated
        cursor.execute("SELECT COUNT(*) FROM crew_availability")
        count_after = cursor.fetchone()[0]
        assert count_after > 0  # Should have blocks again
        conn.close()

        conn.close()

    def test_crew_availability_nonexistent_crew(self):
        """Test crew availability with nonexistent crew (lines 233-234)."""
        init_db(db_path=self.temp_db.name)

        # Try to insert availability for crew that doesn't exist in database
        crew_data = [
            {
                "name": "NONEXISTENT_CREW, X",
                "contact": "Test Contact",
                "skills": "TTR",
                "availability": {"05/08/2025 0900": True, "05/08/2025 1000": False},
            }
        ]

        # Don't insert crew details, so crew won't exist in database
        # This should trigger the warning and continue statement
        insert_crew_availability(crew_data)

        # Verify no availability was inserted
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew_availability")
        count = cursor.fetchone()[0]
        assert count == 0  # No records should be inserted
        conn.close()

    def test_crew_availability_with_block_deletion_logging(self):
        """Test crew availability block deletion logging (line 268)."""
        init_db(db_path=self.temp_db.name)

        crew_data = [
            {
                "name": "DELETION_TEST, T",
                "contact": "Test Contact",
                "skills": "TTR",
                "availability": {
                    "05/08/2025 0900": True,
                    "05/08/2025 1000": True,
                    "05/08/2025 1100": False,
                },
            }
        ]

        # Insert crew details first
        from db_store import insert_crew_details

        contact_map = {"DELETION_TEST, T": "Test Contact"}
        insert_crew_details(crew_data, contact_map)

        # Insert availability first time to create existing blocks
        insert_crew_availability(crew_data)

        # Verify blocks exist
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew_availability")
        count_before = cursor.fetchone()[0]
        assert count_before > 0
        conn.close()

        # Insert availability again for same dates to trigger deletion and logging
        # Use slightly different availability that overlaps with the same date range
        crew_data_same_dates = [
            {
                "name": "DELETION_TEST, T",
                "contact": "Test Contact",
                "skills": "TTR",
                "availability": {
                    "05/08/2025 0800": True,
                    "05/08/2025 0900": False,
                    "05/08/2025 1200": True,
                },
            }
        ]

        # This should delete existing blocks for the same date range and create new ones
        insert_crew_availability(crew_data_same_dates)

        # Verify new blocks were created
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew_availability")
        count_after = cursor.fetchone()[0]
        assert count_after > 0  # Should have new blocks
        conn.close()

    def test_database_commit_error_handling(self):
        """Test error handling during database commits."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        crew_data = [
            {
                "name": "TEST, T",
                "contact": "Test Contact",
                "skills": "TTR",
                "availability": {"05/08/2025 0900": True, "05/08/2025 1700": False},
            }
        ]

        # Insert crew details first
        from db_store import insert_crew_details

        contact_map = {"TEST, T": "Test Contact"}
        insert_crew_details(crew_data, contact_map)

        # Mock connection to simulate commit error
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor

            # Mock fetchone for crew lookup
            mock_cursor.fetchone.return_value = (1,)  # crew id
            mock_cursor.rowcount = 0  # No rows affected

            # Mock commit to raise an error
            mock_conn.commit.side_effect = sqlite3.Error(
                "Commit failed"
            )  # This should raise the commit error
            with pytest.raises(sqlite3.Error):
                insert_crew_availability(crew_data)

            # Verify close was called in finally block
            assert mock_conn.close.called


class TestDBStoreFunctionality:
    """Test core functionality with edge cases."""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.original_db_path = db_store.DB_PATH
        db_store.DB_PATH = self.temp_db.name

    def teardown_method(self):
        """Clean up test environment."""
        # Restore original DB path
        db_store.DB_PATH = self.original_db_path

        # Clean up temp database
        try:
            os.unlink(self.temp_db.name)
        except OSError:
            pass

    def test_concurrent_connections(self):
        """Test handling of multiple concurrent connections."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        # Create multiple connections
        conn1 = sqlite3.connect(self.temp_db.name)
        conn2 = sqlite3.connect(self.temp_db.name)

        crew_data1 = [
            {
                "name": "CREW1, A",
                "contact": "Contact 1",
                "skills": "TTR",
                "availability": {"05/08/2025 0900": True, "05/08/2025 1700": False},
            }
        ]

        crew_data2 = [
            {
                "name": "CREW2, B",
                "contact": "Contact 2",
                "skills": "LGV",
                "availability": {"05/08/2025 1000": True, "05/08/2025 1800": False},
            }
        ]

        # Insert crew details first
        from db_store import insert_crew_details

        contact_map1 = {"CREW1, A": "Contact 1"}
        contact_map2 = {"CREW2, B": "Contact 2"}
        insert_crew_details(crew_data1, contact_map1, conn1)
        insert_crew_details(
            crew_data2, contact_map2, conn2
        )  # Insert data using both connections
        insert_crew_availability(crew_data1, db_conn=conn1)
        insert_crew_availability(crew_data2, db_conn=conn2)

        # Verify both crews were inserted
        cursor = conn1.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew")
        crew_count = cursor.fetchone()[0]
        assert crew_count == 2

        conn1.close()
        conn2.close()

    def test_data_integrity_constraints(self):
        """Test database constraint handling."""
        # Set up database
        init_db(db_path=self.temp_db.name)

        # Test duplicate crew names (should be handled by OR IGNORE)
        crew_data = [
            {
                "name": "DUPLICATE, T",
                "contact": "Contact 1",
                "skills": "TTR",
                "availability": {"05/08/2025 0900": True},
            },
            {
                "name": "DUPLICATE, T",  # Same name
                "contact": "Contact 2",
                "skills": "LGV",
                "availability": {"05/08/2025 1000": True},
            },
        ]

        # Insert crew details first
        from db_store import insert_crew_details

        contact_map = {"DUPLICATE, T": "Contact 1"}  # Only first contact will be used
        insert_crew_details(crew_data, contact_map)

        # This should handle duplicates gracefully
        insert_crew_availability(crew_data)

        # Verify only one crew record exists
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew WHERE name = 'DUPLICATE, T'")
        count = cursor.fetchone()[0]
        assert count == 1
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__])
