"""
Tests for the improved database manager and storage layer.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from database_manager import DatabaseManager, get_database_manager
from db_store_improved import (
    init_db, insert_crew_details, insert_crew_availability,
    insert_appliance_availability, get_database_health, cleanup_old_data,
    _convert_slots_to_blocks
)


class TestDatabaseManager:
    """Test the DatabaseManager class."""
    
    def test_database_manager_initialization(self, tmp_path):
        """Test database manager initialization."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        
        assert manager.db_path == str(db_path)
        assert manager.db_pool is not None
    
    def test_schema_creation(self, tmp_path):
        """Test that schema is created correctly."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.ensure_schema()
        
        # Verify tables exist
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('crew', 'appliance', 'crew_availability', 'appliance_availability', 'schema_version')
            """)
            tables = {row[0] for row in cursor.fetchall()}
            
            expected_tables = {'crew', 'appliance', 'crew_availability', 'appliance_availability', 'schema_version'}
            assert tables == expected_tables
    
    def test_schema_version_tracking(self, tmp_path):
        """Test schema version is tracked correctly."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.ensure_schema()
        
        version = manager._get_schema_version()
        assert version == 1
    
    def test_connection_context_manager(self, tmp_path):
        """Test connection context manager works."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.ensure_schema()
        
        with manager.get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_transaction_context_manager(self, tmp_path):
        """Test transaction context manager with commit."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.ensure_schema()
        
        with manager.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO crew (name) VALUES ('Test User')")
        
        # Verify data was committed
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM crew WHERE name = 'Test User'")
            result = cursor.fetchone()
            assert result[0] == "Test User"
    
    def test_transaction_rollback(self, tmp_path):
        """Test transaction rollback on error."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.ensure_schema()
        
        try:
            with manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO crew (name) VALUES ('Test User')")
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify data was rolled back
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM crew WHERE name = 'Test User'")
            count = cursor.fetchone()[0]
            assert count == 0
    
    def test_upsert_crew_member(self, tmp_path):
        """Test crew member upsert functionality."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.ensure_schema()
        
        crew_data = {
            'name': 'John Doe',
            'role': 'Firefighter',
            'contact': '555-1234',
            'skills': 'First Aid'
        }
        
        crew_id = manager.upsert_crew_member(crew_data)
        assert isinstance(crew_id, int)
        
        # Test update
        crew_data['role'] = 'Senior Firefighter'
        crew_id2 = manager.upsert_crew_member(crew_data)
        assert crew_id == crew_id2
        
        # Verify update
        crew_info = manager.get_crew_by_name('John Doe')
        assert crew_info['role'] == 'Senior Firefighter'
    
    def test_batch_upsert_crew(self, tmp_path):
        """Test batch crew upsert."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.ensure_schema()
        
        crew_list = [
            {'name': 'John Doe', 'role': 'Firefighter', 'contact': '555-1234'},
            {'name': 'Jane Smith', 'role': 'Paramedic', 'contact': '555-5678'},
        ]
        
        manager.batch_upsert_crew(crew_list)
        
        # Verify both crew members exist
        john = manager.get_crew_by_name('John Doe')
        jane = manager.get_crew_by_name('Jane Smith')
        
        assert john is not None
        assert jane is not None
        assert john['role'] == 'Firefighter'
        assert jane['role'] == 'Paramedic'
    
    def test_clean_old_availability_data(self, tmp_path):
        """Test cleaning old availability data."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        manager.ensure_schema()
        
        # Add some test data
        crew_id = manager.upsert_crew_member({'name': 'Test User'})
        
        # Add old and new availability data
        old_time = datetime.now() - timedelta(days=35)
        recent_time = datetime.now() - timedelta(days=5)
        
        with manager.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO crew_availability (crew_id, start_time, end_time)
                VALUES (?, ?, ?)
            """, (crew_id, old_time, old_time + timedelta(hours=1)))
            
            cursor.execute("""
                INSERT INTO crew_availability (crew_id, start_time, end_time)
                VALUES (?, ?, ?)
            """, (crew_id, recent_time, recent_time + timedelta(hours=1)))
        
        # Clean data older than 30 days
        deleted_count = manager.clean_old_availability_data(30)
        assert deleted_count == 1
        
        # Verify only recent data remains
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM crew_availability")
            remaining_count = cursor.fetchone()[0]
            assert remaining_count == 1


class TestSlotConversion:
    """Test availability slot conversion."""
    
    def test_convert_empty_slots(self):
        """Test converting empty availability slots."""
        result = _convert_slots_to_blocks({})
        assert result == []
    
    def test_convert_single_slot(self):
        """Test converting single available slot."""
        availability = {"05/08/2025 0800": True}
        blocks = _convert_slots_to_blocks(availability)
        
        assert len(blocks) == 1
        assert blocks[0]['start_time'] == datetime(2025, 8, 5, 8, 0)
        assert blocks[0]['end_time'] == datetime(2025, 8, 5, 8, 15)
    
    def test_convert_continuous_slots(self):
        """Test converting continuous available slots."""
        availability = {
            "05/08/2025 0800": True,
            "05/08/2025 0815": True,
            "05/08/2025 0830": True
        }
        blocks = _convert_slots_to_blocks(availability)
        
        assert len(blocks) == 1
        assert blocks[0]['start_time'] == datetime(2025, 8, 5, 8, 0)
        assert blocks[0]['end_time'] == datetime(2025, 8, 5, 8, 45)
    
    def test_convert_discontinuous_slots(self):
        """Test converting discontinuous available slots."""
        availability = {
            "05/08/2025 0800": True,
            "05/08/2025 0815": True,
            "05/08/2025 0830": False,
            "05/08/2025 0845": True,
            "05/08/2025 0900": True
        }
        blocks = _convert_slots_to_blocks(availability)
        
        assert len(blocks) == 2
        assert blocks[0]['start_time'] == datetime(2025, 8, 5, 8, 0)
        assert blocks[0]['end_time'] == datetime(2025, 8, 5, 8, 30)
        assert blocks[1]['start_time'] == datetime(2025, 8, 5, 8, 45)
        assert blocks[1]['end_time'] == datetime(2025, 8, 5, 9, 15)
    
    def test_convert_invalid_time_format(self):
        """Test handling invalid time formats."""
        availability = {
            "invalid-time": True,
            "05/08/2025 0800": True
        }
        
        with patch('db_store_improved.logger') as mock_logger:
            blocks = _convert_slots_to_blocks(availability)
            
            # Should log warning for invalid format
            mock_logger.warning.assert_called_once()
            
            # Should still process valid times
            assert len(blocks) == 1
            assert blocks[0]['start_time'] == datetime(2025, 8, 5, 8, 0)


class TestImprovedStorage:
    """Test improved storage functions."""
    
    def test_insert_crew_details_improved(self, tmp_path):
        """Test improved crew details insertion."""
        # Mock the database manager to use temporary path
        with patch('db_store_improved.get_database_manager') as mock_get_manager:
            manager = DatabaseManager(str(tmp_path / "test.db"))
            manager.ensure_schema()
            mock_get_manager.return_value = manager
            
            crew_list = [
                {'name': 'John Doe', 'role': 'Firefighter', 'skills': 'First Aid'},
                {'name': 'Jane Smith', 'role': 'Paramedic', 'skills': 'Advanced Life Support'}
            ]
            contact_map = {'John Doe': '555-1234', 'Jane Smith': '555-5678'}
            
            insert_crew_details(crew_list, contact_map)
            
            # Verify data was inserted
            john = manager.get_crew_by_name('John Doe')
            jane = manager.get_crew_by_name('Jane Smith')
            
            assert john is not None
            assert jane is not None
            assert john['contact'] == '555-1234'
            assert jane['contact'] == '555-5678'
    
    def test_insert_crew_availability_improved(self, tmp_path):
        """Test improved crew availability insertion."""
        with patch('db_store_improved.get_database_manager') as mock_get_manager:
            manager = DatabaseManager(str(tmp_path / "test.db"))
            manager.ensure_schema()
            mock_get_manager.return_value = manager
            
            # First add crew
            crew_id = manager.upsert_crew_member({'name': 'John Doe'})
            
            crew_list = [{
                'name': 'John Doe',
                'availability': {
                    '05/08/2025 0800': True,
                    '05/08/2025 0815': True,
                    '05/08/2025 0830': False,
                    '05/08/2025 0845': True
                }
            }]
            
            insert_crew_availability(crew_list)
            
            # Verify availability blocks were created
            stats = manager.get_database_stats()
            assert stats['crew_availability'] >= 2  # Should create 2 blocks
    
    def test_insert_appliance_availability_improved(self, tmp_path):
        """Test improved appliance availability insertion."""
        with patch('db_store_improved.get_database_manager') as mock_get_manager:
            manager = DatabaseManager(str(tmp_path / "test.db"))
            manager.ensure_schema()
            mock_get_manager.return_value = manager
            
            appliance_obj = {
                'Engine 1': {
                    'availability': {
                        '05/08/2025 0800': True,
                        '05/08/2025 0815': True
                    }
                }
            }
            
            insert_appliance_availability(appliance_obj)
            
            # Verify appliance and availability were created
            stats = manager.get_database_stats()
            assert stats['appliance'] >= 1
            assert stats['appliance_availability'] >= 1
    
    def test_get_database_health(self, tmp_path):
        """Test database health reporting."""
        with patch('db_store_improved.get_database_manager') as mock_get_manager:
            manager = DatabaseManager(str(tmp_path / "test.db"))
            manager.ensure_schema()
            mock_get_manager.return_value = manager
            
            # Add some test data
            manager.upsert_crew_member({'name': 'Test User'})
            
            health = get_database_health()
            
            assert 'stats' in health
            assert 'healthy' in health
            assert health['healthy'] is True  # Has crew data
            assert health['stats']['crew'] == 1
    
    def test_cleanup_old_data(self, tmp_path):
        """Test cleanup function."""
        with patch('db_store_improved.get_database_manager') as mock_get_manager:
            manager = DatabaseManager(str(tmp_path / "test.db"))
            manager.ensure_schema()
            mock_get_manager.return_value = manager
            
            # Mock the cleanup method
            manager.clean_old_availability_data = MagicMock(return_value=5)
            
            result = cleanup_old_data(30)
            
            assert result == 5
            manager.clean_old_availability_data.assert_called_once_with(30)


class TestGlobalManager:
    """Test global database manager singleton."""
    
    def test_get_database_manager_singleton(self):
        """Test that get_database_manager returns singleton."""
        # Reset global state
        import database_manager
        database_manager._db_manager = None
        
        manager1 = get_database_manager()
        manager2 = get_database_manager()
        
        assert manager1 is manager2
    
    def test_get_database_manager_different_paths(self):
        """Test that different paths create different managers."""
        # Reset global state
        import database_manager
        database_manager._db_manager = None
        
        manager1 = get_database_manager("db1.db")
        
        # Reset for different path
        database_manager._db_manager = None
        manager2 = get_database_manager("db2.db")
        
        assert manager1.db_path != manager2.db_path


if __name__ == "__main__":
    pytest.main([__file__])
