"""
Comprehensive tests for Phase 2 Error Handling & Logging improvements.

Tests the integrated error handling, robust operations, and monitoring systems.
"""

import pytest
import sqlite3
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import our Phase 2 modules
from error_logging_integration import (
    IntegratedErrorLogger, OperationContext, robust_operation,
    HealthMonitor, get_integrated_logger, get_health_monitor
)
from robust_operations import (
    RobustDatabaseManager, SmartCacheManager,
    get_robust_database_manager, get_cache_manager
)
from robust_network import (
    RobustSession, ConnectionManager, NetworkConfig,
    get_robust_session, get_connection_manager, smart_delay
)
from error_handling import ErrorCategory, ErrorSeverity, DatabaseError, NetworkError


class TestIntegratedErrorLogger:
    """Test the integrated error logger."""
    
    def test_operation_context_success(self):
        """Test successful operation context."""
        logger = IntegratedErrorLogger()
        context = OperationContext(
            operation_name="test_operation",
            component="test_component"
        )
        
        result = None
        with logger.operation_context(context):
            result = "success"
        
        assert result == "success"
    
    def test_operation_context_with_error(self):
        """Test operation context with error handling."""
        logger = IntegratedErrorLogger()
        context = OperationContext(
            operation_name="test_operation",
            component="test_component"
        )
        
        with pytest.raises(MemoryError):
            with logger.operation_context(context):
                raise MemoryError("Test fatal error")
    
    def test_safe_operation_success(self):
        """Test safe operation execution."""
        logger = IntegratedErrorLogger()
        
        def test_func(x, y):
            return x + y
        
        result = logger.safe_operation(
            "test_add",
            "math",
            test_func,
            2, 3
        )
        
        assert result == 5
    
    def test_safe_operation_with_retry(self):
        """Test safe operation with retry logic."""
        logger = IntegratedErrorLogger()
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = logger.safe_operation(
            "test_retry",
            "test",
            failing_func,
            max_retries=3,
            retry_delay=0.01
        )
        
        assert result == "success"
        assert call_count == 3
    
    def test_robust_operation_decorator(self):
        """Test the robust operation decorator."""
        
        @robust_operation(
            operation_name="test_decorated",
            component="test",
            max_retries=2,
            retry_delay=0.01
        )
        def test_function(value):
            if value < 0:
                raise ValueError("Negative value")
            return value * 2
        
        # Test success
        assert test_function(5) == 10
        
        # Test with exception
        with pytest.raises(ValueError):
            test_function(-1)


class TestHealthMonitor:
    """Test the health monitoring system."""
    
    def test_health_monitor_creation(self):
        """Test health monitor creation."""
        monitor = HealthMonitor()
        assert monitor.start_time is not None
        assert isinstance(monitor.health_checks, dict)
    
    def test_add_health_check(self):
        """Test adding health checks."""
        monitor = HealthMonitor()
        
        def check_func():
            return True
        
        monitor.add_health_check("test_check", check_func)
        assert "test_check" in monitor.health_checks
    
    def test_get_health_status_healthy(self):
        """Test health status when all checks pass."""
        monitor = HealthMonitor()
        
        monitor.add_health_check("always_pass", lambda: True)
        monitor.add_health_check("also_pass", lambda: True)
        
        status = monitor.get_health_status()
        
        assert status['overall_status'] == 'healthy'
        assert 'timestamp' in status
        assert 'uptime_seconds' in status
        assert status['health_checks']['always_pass']['status'] == 'pass'
        assert status['health_checks']['also_pass']['status'] == 'pass'
    
    def test_get_health_status_degraded(self):
        """Test health status when some checks fail."""
        monitor = HealthMonitor()
        
        monitor.add_health_check("pass_check", lambda: True)
        monitor.add_health_check("fail_check", lambda: False)
        
        status = monitor.get_health_status()
        
        assert status['overall_status'] == 'degraded'
        assert status['health_checks']['pass_check']['status'] == 'pass'
        assert status['health_checks']['fail_check']['status'] == 'fail'
    
    def test_get_health_status_with_exception(self):
        """Test health status when check raises exception."""
        monitor = HealthMonitor()
        
        def error_check():
            raise RuntimeError("Check failed")
        
        monitor.add_health_check("error_check", error_check)
        
        status = monitor.get_health_status()
        
        assert status['overall_status'] == 'unhealthy'
        assert status['health_checks']['error_check']['status'] == 'error'
        assert 'error' in status['health_checks']['error_check']


class TestRobustDatabaseManager:
    """Test the robust database manager."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    
    def test_database_manager_creation(self, temp_db):
        """Test robust database manager creation."""
        manager = RobustDatabaseManager(temp_db)
        assert manager.db_path == temp_db
        assert manager.connection_health.is_healthy
    
    def test_execute_query_success(self, temp_db):
        """Test successful query execution."""
        manager = RobustDatabaseManager(temp_db)
        
        # Create table
        manager.execute_query(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
        )
        
        # Insert data
        rowcount = manager.execute_query(
            "INSERT INTO test (name) VALUES (?)",
            ("test_name",)
        )
        
        assert rowcount == 1
        
        # Query data
        result = manager.execute_query(
            "SELECT name FROM test WHERE id = ?",
            (1,),
            fetch_one=True
        )
        
        assert result[0] == "test_name"
    
    def test_batch_insert(self, temp_db):
        """Test batch insert functionality."""
        manager = RobustDatabaseManager(temp_db)
        
        # Create table
        manager.execute_query(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)"
        )
        
        # Batch insert
        data = [
            {"name": "item1", "value": 10},
            {"name": "item2", "value": 20},
            {"name": "item3", "value": 30}
        ]
        
        rowcount = manager.batch_insert("test", data)
        assert rowcount == 3
        
        # Verify data
        results = manager.execute_query(
            "SELECT COUNT(*) FROM test",
            fetch_one=True
        )
        assert results[0] == 3
    
    def test_transaction_success(self, temp_db):
        """Test successful transaction execution."""
        manager = RobustDatabaseManager(temp_db)
        
        # Create table
        manager.execute_query(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
        )
        
        def operation1(cursor):
            cursor.execute("INSERT INTO test (name) VALUES (?)", ("test1",))
        
        def operation2(cursor):
            cursor.execute("INSERT INTO test (name) VALUES (?)", ("test2",))
        
        result = manager.execute_transaction([operation1, operation2])
        assert result is True
        
        # Verify both records were inserted
        count = manager.execute_query(
            "SELECT COUNT(*) FROM test",
            fetch_one=True
        )[0]
        assert count == 2
    
    def test_connection_health_check(self, temp_db):
        """Test connection health checking."""
        manager = RobustDatabaseManager(temp_db)
        
        # Should be healthy initially
        assert manager.check_connection_health() is True
        assert manager.connection_health.is_healthy is True
    
    def test_get_health_status(self, temp_db):
        """Test health status reporting."""
        manager = RobustDatabaseManager(temp_db)
        
        status = manager.get_health_status()
        
        assert 'is_healthy' in status
        assert 'last_check_age_seconds' in status
        assert 'error_count' in status
        assert 'database_path' in status
        assert status['database_path'] == temp_db


class TestSmartCacheManager:
    """Test the smart cache manager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_cache_manager_creation(self):
        """Test cache manager creation."""
        manager = SmartCacheManager()
        assert manager.cache_dir == "_cache"
    
    def test_write_and_read_cache(self, temp_dir):
        """Test cache write and read operations."""
        manager = SmartCacheManager(temp_dir)
        
        file_path = os.path.join(temp_dir, "test_file.txt")
        test_content = "This is test content"
        
        # Write cache
        success = manager.write_cache_file(file_path, test_content)
        assert success is True
        
        # Read cache
        content = manager.read_cache_file(file_path)
        assert content == test_content
    
    def test_read_nonexistent_cache(self, temp_dir):
        """Test reading non-existent cache file."""
        manager = SmartCacheManager(temp_dir)
        
        file_path = os.path.join(temp_dir, "nonexistent.txt")
        content = manager.read_cache_file(file_path)
        assert content is None
    
    def test_write_cache_with_directories(self, temp_dir):
        """Test cache write with directory creation."""
        manager = SmartCacheManager(temp_dir)
        
        file_path = os.path.join(temp_dir, "subdir", "test_file.txt")
        test_content = "Test content in subdirectory"
        
        success = manager.write_cache_file(file_path, test_content, create_dirs=True)
        assert success is True
        
        # Verify file exists and content is correct
        assert os.path.exists(file_path)
        content = manager.read_cache_file(file_path)
        assert content == test_content


class TestRobustNetwork:
    """Test the robust network operations."""
    
    def test_network_config(self):
        """Test network configuration."""
        config = NetworkConfig()
        assert config.max_retries == 3
        assert config.timeout == (10, 30)
        assert isinstance(config.retry_on_status, tuple)
    
    def test_robust_session_creation(self):
        """Test robust session creation."""
        session = RobustSession()
        assert session.config is not None
        assert session.session is not None
        assert session._request_count == 0
        assert session._error_count == 0
    
    @patch('requests.Session.request')
    def test_successful_request(self, mock_request):
        """Test successful HTTP request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"Success"
        mock_response.text = "Success"
        mock_request.return_value = mock_response
        
        session = RobustSession()
        response = session.get("http://example.com", description="test request")
        
        assert response.status_code == 200
        assert session._request_count == 1
        assert session._error_count == 0
    
    @patch('requests.Session.request')
    def test_http_error_handling(self, mock_request):
        """Test HTTP error handling."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.content = b"Server Error"
        mock_response.text = "Server Error"
        mock_request.return_value = mock_response
        
        session = RobustSession()
        
        with pytest.raises(NetworkError):
            session.get("http://example.com", description="test request")
        
        assert session._error_count == 1
    
    def test_connection_manager(self):
        """Test connection manager functionality."""
        manager = ConnectionManager(max_sessions=2)
        
        # Get session
        session1 = manager.get_session("session1")
        assert isinstance(session1, RobustSession)
        assert len(manager.sessions) == 1
        
        # Get another session
        session2 = manager.get_session("session2")
        assert len(manager.sessions) == 2
        
        # Get health status
        status = manager.get_health_status()
        assert status['active_sessions'] == 2
        assert status['max_sessions'] == 2
    
    def test_smart_delay(self):
        """Test smart delay calculation."""
        # Test basic exponential backoff
        delay1 = smart_delay(0, base_delay=1.0, jitter=False)
        delay2 = smart_delay(1, base_delay=1.0, jitter=False)
        delay3 = smart_delay(2, base_delay=1.0, jitter=False)
        
        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0
        
        # Test max delay cap
        delay_max = smart_delay(10, base_delay=1.0, max_delay=5.0, jitter=False)
        assert delay_max == 5.0
        
        # Test jitter (should be different each time)
        delay_jitter1 = smart_delay(2, base_delay=1.0, jitter=True)
        delay_jitter2 = smart_delay(2, base_delay=1.0, jitter=True)
        # With jitter, values should be around 4.0 but different
        assert 3.0 <= delay_jitter1 <= 5.0
        assert 3.0 <= delay_jitter2 <= 5.0


class TestGlobalInstances:
    """Test global instance management."""
    
    def test_get_integrated_logger(self):
        """Test getting global integrated logger."""
        logger1 = get_integrated_logger()
        logger2 = get_integrated_logger()
        assert logger1 is logger2  # Should be same instance
    
    def test_get_health_monitor(self):
        """Test getting global health monitor."""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()
        assert monitor1 is monitor2  # Should be same instance
    
    def test_get_robust_database_manager(self):
        """Test getting robust database manager."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            manager1 = get_robust_database_manager(db_path)
            manager2 = get_robust_database_manager(db_path)
            assert manager1 is manager2  # Should be same instance for same path
            
            # Different path should give different instance
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f2:
                db_path2 = f2.name
            
            try:
                manager3 = get_robust_database_manager(db_path2)
                assert manager1 is not manager3
            finally:
                try:
                    os.unlink(db_path2)
                except FileNotFoundError:
                    pass
        
        finally:
            try:
                os.unlink(db_path)
            except FileNotFoundError:
                pass
    
    def test_get_cache_manager(self):
        """Test getting global cache manager."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        assert manager1 is manager2  # Should be same instance
    
    def test_get_connection_manager(self):
        """Test getting global connection manager."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()
        assert manager1 is manager2  # Should be same instance
    
    def test_get_robust_session(self):
        """Test getting robust session from connection manager."""
        session1 = get_robust_session("test_session")
        session2 = get_robust_session("test_session")
        assert session1 is session2  # Should be same instance for same ID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
