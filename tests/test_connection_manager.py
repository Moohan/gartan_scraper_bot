#!/usr/bin/env python3
"""Comprehensive tests for connection_manager.py functionality."""

import os
import sqlite3
import tempfile
from unittest.mock import Mock, patch

import pytest

import connection_manager
from connection_manager import (
    DB_PATH,
    get_connection,
    get_database_pool,
    get_session_manager,
)


class TestConnectionManagerDatabase:
    """Test database connection functionality."""

    def test_get_database_pool_context_manager(self):
        """Test get_database_pool context manager functionality (lines 15-20)."""
        # Use a temporary database for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            with patch.object(connection_manager, "DB_PATH", temp_db_path):
                # Test context manager usage
                with get_database_pool() as conn:
                    assert isinstance(conn, sqlite3.Connection)
                    assert conn.row_factory == sqlite3.Row

                    # Test that connection is working
                    cursor = conn.cursor()
                    cursor.execute("CREATE TABLE test (id INTEGER)")
                    cursor.execute("INSERT INTO test (id) VALUES (1)")
                    conn.commit()

                    # Verify data was inserted
                    cursor.execute("SELECT * FROM test")
                    rows = cursor.fetchall()
                    assert len(rows) == 1
                    assert rows[0]["id"] == 1

                # After context manager exits, connection should be closed
                with pytest.raises(sqlite3.ProgrammingError):
                    # Attempting to use closed connection should raise error
                    conn.execute("SELECT 1")

        finally:
            # Clean up temporary database
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)

    def test_get_database_pool_exception_handling(self):
        """Test get_database_pool exception handling and cleanup."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            with patch.object(connection_manager, "DB_PATH", temp_db_path):
                # Test that connection is properly closed even when exception occurs
                with pytest.raises(ValueError):
                    with get_database_pool() as conn:
                        assert isinstance(conn, sqlite3.Connection)
                        # Simulate an error within the context
                        raise ValueError("Test error")

                # Connection should still be closed despite the exception
                with pytest.raises(sqlite3.ProgrammingError):
                    conn.execute("SELECT 1")

        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)

    def test_get_connection_direct(self):
        """Test get_connection direct connection functionality (lines 25-27)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            with patch.object(connection_manager, "DB_PATH", temp_db_path):
                # Test direct connection
                conn = get_connection()

                assert isinstance(conn, sqlite3.Connection)
                assert conn.row_factory == sqlite3.Row

                # Test that connection is working
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
                cursor.execute("INSERT INTO test (id, name) VALUES (1, 'test')")
                conn.commit()

                # Verify data was inserted
                cursor.execute("SELECT * FROM test")
                rows = cursor.fetchall()
                assert len(rows) == 1
                assert rows[0]["id"] == 1
                assert rows[0]["name"] == "test"

                # Manual cleanup required for direct connection
                conn.close()

        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)

    def test_get_connection_multiple_connections(self):
        """Test getting multiple connections simultaneously."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            with patch.object(connection_manager, "DB_PATH", temp_db_path):
                # Get multiple connections
                conn1 = get_connection()
                conn2 = get_connection()

                assert isinstance(conn1, sqlite3.Connection)
                assert isinstance(conn2, sqlite3.Connection)
                assert conn1 != conn2  # Should be different connection objects

                # Both should work independently
                cursor1 = conn1.cursor()
                cursor2 = conn2.cursor()

                cursor1.execute("CREATE TABLE test1 (id INTEGER)")
                cursor2.execute("CREATE TABLE test2 (id INTEGER)")

                conn1.commit()
                conn2.commit()

                # Verify both tables exist
                cursor1.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor1.fetchall()]
                assert "test1" in tables
                assert "test2" in tables

                conn1.close()
                conn2.close()

        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)

    def test_database_path_configuration(self):
        """Test database path configuration."""
        # Test that DB_PATH is properly configured
        assert DB_PATH == "gartan_availability.db"

        # Test with custom DB_PATH
        custom_path = "test_custom.db"
        with patch.object(connection_manager, "DB_PATH", custom_path):
            with patch("sqlite3.connect") as mock_connect:
                mock_conn = Mock()
                mock_connect.return_value = mock_conn

                get_connection()

                # Verify connect was called with custom path
                mock_connect.assert_called_once_with(custom_path)
                mock_conn.row_factory = sqlite3.Row


class TestConnectionManagerSession:
    """Test session manager functionality."""

    def test_get_session_manager(self):
        """Test get_session_manager functionality (lines 31-33)."""
        session = get_session_manager()

        # Should return a requests Session object
        import requests

        assert isinstance(session, requests.Session)

        # Should be a fresh session each time
        session2 = get_session_manager()
        assert isinstance(session2, requests.Session)
        assert session != session2  # Different session objects

    def test_session_manager_functionality(self):
        """Test that returned session manager works properly."""
        session = get_session_manager()

        # Test that it has expected session methods
        assert hasattr(session, "get")
        assert hasattr(session, "post")
        assert hasattr(session, "put")
        assert hasattr(session, "delete")
        assert hasattr(session, "headers")
        assert hasattr(session, "cookies")

        # Test that headers can be set
        session.headers.update({"User-Agent": "Test Agent"})
        assert session.headers["User-Agent"] == "Test Agent"

    def test_multiple_session_managers(self):
        """Test getting multiple session managers."""
        sessions = []
        for i in range(3):
            session = get_session_manager()
            sessions.append(session)

        # All should be different objects
        for i in range(len(sessions)):
            for j in range(i + 1, len(sessions)):
                assert sessions[i] != sessions[j]

        # All should be Session instances
        import requests

        for session in sessions:
            assert isinstance(session, requests.Session)


class TestConnectionManagerIntegration:
    """Integration tests for connection manager."""

    def test_database_pool_vs_direct_connection(self):
        """Test that both connection methods work with same database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            with patch.object(connection_manager, "DB_PATH", temp_db_path):
                # Create table using context manager
                with get_database_pool() as conn1:
                    cursor = conn1.cursor()
                    cursor.execute(
                        "CREATE TABLE integration_test (id INTEGER, value TEXT)"
                    )
                    cursor.execute(
                        "INSERT INTO integration_test (id, value) VALUES (1, 'pool')"
                    )
                    conn1.commit()

                # Read data using direct connection
                conn2 = get_connection()
                cursor = conn2.cursor()
                cursor.execute("SELECT * FROM integration_test")
                rows = cursor.fetchall()

                assert len(rows) == 1
                assert rows[0]["id"] == 1
                assert rows[0]["value"] == "pool"

                # Add more data using direct connection
                cursor.execute(
                    "INSERT INTO integration_test (id, value) VALUES (2, 'direct')"
                )
                conn2.commit()
                conn2.close()

                # Verify using context manager
                with get_database_pool() as conn3:
                    cursor = conn3.cursor()
                    cursor.execute("SELECT COUNT(*) as count FROM integration_test")
                    count = cursor.fetchone()["count"]
                    assert count == 2

        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)

    def test_connection_error_handling(self):
        """Test connection error handling scenarios."""
        # Test with invalid database path
        invalid_path = "/invalid/nonexistent/path/test.db"

        with patch.object(connection_manager, "DB_PATH", invalid_path):
            # Should handle connection errors gracefully
            with pytest.raises(sqlite3.OperationalError):
                with get_database_pool():
                    pass

            with pytest.raises(sqlite3.OperationalError):
                get_connection()
