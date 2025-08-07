#!/usr/bin/env python3
"""
Test the connection management optimizations.
"""

import pytest
import time
import threading
from connection_manager import (
    SessionManager,
    DatabasePool,
    get_session_manager,
    get_database_pool,
    close_all_connections
)


def test_session_manager_basic():
    """Test basic session manager functionality."""
    manager = SessionManager()
    
    # First session
    session1 = manager.get_session()
    assert session1 is not None
    assert hasattr(session1, 'headers')
    
    # Should reuse the same session
    session2 = manager.get_session()
    assert session1 is session2
    
    manager.close()


def test_session_manager_timeout():
    """Test session timeout and renewal."""
    manager = SessionManager()
    manager._session_timeout = 0.1  # Very short timeout for testing
    
    session1 = manager.get_session()
    
    # Wait for timeout
    time.sleep(0.2)
    
    # Should create a new session
    session2 = manager.get_session()
    assert session1 is not session2
    
    manager.close()


def test_database_pool_basic():
    """Test basic database pool functionality."""
    pool = DatabasePool(":memory:", max_connections=2)
    
    # Test context manager
    with pool.get_connection() as conn:
        assert conn is not None
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
    
    pool.close_all()


def test_database_pool_concurrency():
    """Test database pool with multiple connections."""
    pool = DatabasePool(":memory:", max_connections=2)
    results = []
    
    def worker(worker_id):
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ?", (worker_id,))
            result = cursor.fetchone()
            results.append(result[0])
    
    # Start multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # Check results
    assert len(results) == 5
    assert sorted(results) == [0, 1, 2, 3, 4]
    
    pool.close_all()


def test_global_managers():
    """Test global manager instances."""
    manager1 = get_session_manager()
    manager2 = get_session_manager()
    assert manager1 is manager2
    
    pool1 = get_database_pool(":memory:")
    pool2 = get_database_pool(":memory:")
    assert pool1 is pool2
    
    # Different path should create new pool
    pool3 = get_database_pool("test.db")
    assert pool1 is not pool3
    
    close_all_connections()


if __name__ == "__main__":
    print("Testing connection manager optimizations...")
    test_session_manager_basic()
    print("✅ Basic session manager test passed")
    
    test_session_manager_timeout()
    print("✅ Session timeout test passed")
    
    test_database_pool_basic()
    print("✅ Basic database pool test passed")
    
    test_database_pool_concurrency()
    print("✅ Database pool concurrency test passed")
    
    test_global_managers()
    print("✅ Global managers test passed")
    
    print("\n🚀 All connection manager tests passed!")
