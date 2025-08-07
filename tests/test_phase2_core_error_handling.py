"""
Simplified tests for Phase 2 Error Handling & Logging improvements.

Tests core functionality without full configuration dependencies.
"""

import pytest
import sqlite3
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import only core error handling components that don't require full config
from error_handling import (
    ErrorHandler, ErrorInfo, ErrorCategory, ErrorSeverity,
    get_error_handler, GartanError, DatabaseError, NetworkError
)


class TestErrorHandling:
    """Test core error handling functionality."""
    
    def test_error_handler_creation(self):
        """Test error handler creation."""
        handler = ErrorHandler()
        assert handler.error_stats['total_errors'] == 0
        assert isinstance(handler.error_stats['errors_by_category'], dict)
        assert isinstance(handler.error_stats['errors_by_severity'], dict)
    
    def test_classify_exception_database_error(self):
        """Test classifying database exceptions."""
        handler = ErrorHandler()
        
        # Test SQLite error classification
        sqlite_error = sqlite3.OperationalError("database is locked")
        error_info = handler.classify_exception(sqlite_error)
        
        assert error_info.category == ErrorCategory.DATABASE
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert "database is locked" in error_info.message
    
    def test_classify_exception_network_error(self):
        """Test classifying network exceptions."""
        handler = ErrorHandler()
        
        # Test connection error classification
        import requests
        connection_error = requests.ConnectionError("Connection failed")
        error_info = handler.classify_exception(connection_error)
        
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.severity == ErrorSeverity.MEDIUM
    
    def test_handle_error_logging(self):
        """Test error handling and logging."""
        handler = ErrorHandler()
        
        error_info = ErrorInfo(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            message="Test error",
            recoverable=True
        )
        
        # Should return True for recoverable medium severity error
        result = handler.handle_error(error_info, "test_context")
        assert result is True
        
        # Check stats updated
        assert handler.error_stats['total_errors'] == 1
        assert handler.error_stats['errors_by_category']['database'] == 1
        assert handler.error_stats['errors_by_severity']['medium'] == 1
    
    def test_handle_error_fatal(self):
        """Test handling fatal errors."""
        handler = ErrorHandler()
        
        error_info = ErrorInfo(
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.FATAL,
            message="Fatal configuration error",
            recoverable=False
        )
        
        # Should return False for fatal errors
        result = handler.handle_error(error_info, "test_context")
        assert result is False
        
        assert handler.error_stats['fatal_errors'] == 1
    
    def test_get_statistics(self):
        """Test getting error statistics."""
        handler = ErrorHandler()
        
        # Add some errors
        error1 = ErrorInfo(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.LOW,
            message="Network error"
        )
        error2 = ErrorInfo(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            message="Database error"
        )
        
        handler.handle_error(error1, "context1")
        handler.handle_error(error2, "context2")
        
        stats = handler.get_statistics()
        
        assert stats['total_errors'] == 2
        assert stats['by_category']['network'] == 1
        assert stats['by_category']['database'] == 1
        assert stats['by_severity']['low'] == 1
        assert stats['by_severity']['high'] == 1
    
    def test_with_retry_success(self):
        """Test retry mechanism with eventual success."""
        handler = ErrorHandler()
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = handler.with_retry(failing_func, max_retries=3, delay=0.01)
        assert result == "success"
        assert call_count == 3
    
    def test_with_retry_failure(self):
        """Test retry mechanism with persistent failure."""
        handler = ErrorHandler()
        
        def always_fail():
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError):
            handler.with_retry(always_fail, max_retries=2, delay=0.01)


class TestGartanExceptions:
    """Test custom Gartan exception classes."""
    
    def test_gartan_error_creation(self):
        """Test creating base Gartan error."""
        error_info = ErrorInfo(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            message="Validation failed"
        )
        
        exception = GartanError(error_info)
        assert str(exception) == "Validation failed"
        assert exception.error_info == error_info
    
    def test_gartan_error_to_dict(self):
        """Test converting Gartan error to dictionary."""
        error_info = ErrorInfo(
            category=ErrorCategory.PARSING,
            severity=ErrorSeverity.LOW,
            message="Parse error",
            details={"line": 42}
        )
        
        exception = GartanError(error_info)
        error_dict = exception.to_dict()
        
        assert error_dict['category'] == 'parsing'
        assert error_dict['severity'] == 'low'
        assert error_dict['message'] == 'Parse error'
        assert error_dict['details'] == {"line": 42}
        assert 'timestamp' in error_dict
    
    def test_database_error(self):
        """Test database-specific error."""
        error_info = ErrorInfo(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            message="Database connection failed"
        )
        
        original_exception = sqlite3.OperationalError("database is locked")
        db_error = DatabaseError(error_info, original_exception)
        
        assert isinstance(db_error, GartanError)
        assert db_error.original_exception == original_exception
    
    def test_network_error(self):
        """Test network-specific error."""
        error_info = ErrorInfo(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network request failed"
        )
        
        import requests
        original_exception = requests.ConnectionError("Connection refused")
        net_error = NetworkError(error_info, original_exception)
        
        assert isinstance(net_error, GartanError)
        assert net_error.original_exception == original_exception


class TestErrorSeverityDetermination:
    """Test error severity determination logic."""
    
    def test_network_error_severity(self):
        """Test network error severity determination."""
        handler = ErrorHandler()
        
        # Connection errors should be medium severity
        import requests
        conn_error = requests.ConnectionError("Connection failed")
        error_info = handler.classify_exception(conn_error)
        assert error_info.severity == ErrorSeverity.MEDIUM
        
        # Timeout errors should be medium severity
        timeout_error = requests.Timeout("Request timed out")
        error_info = handler.classify_exception(timeout_error)
        assert error_info.severity == ErrorSeverity.MEDIUM
    
    def test_database_error_severity(self):
        """Test database error severity determination."""
        handler = ErrorHandler()
        
        # Locked database should be medium severity
        locked_db = sqlite3.OperationalError("database is locked")
        error_info = handler.classify_exception(locked_db)
        assert error_info.severity == ErrorSeverity.MEDIUM
        
        # Missing table should be high severity
        missing_table = sqlite3.OperationalError("no such table: test")
        error_info = handler.classify_exception(missing_table)
        assert error_info.severity == ErrorSeverity.HIGH
        
        # Integrity errors should be low severity (constraint violations)
        integrity_error = sqlite3.IntegrityError("UNIQUE constraint failed")
        error_info = handler.classify_exception(integrity_error)
        assert error_info.severity == ErrorSeverity.LOW
    
    def test_file_error_severity(self):
        """Test file operation error severity determination."""
        handler = ErrorHandler()
        
        # File not found should be low severity
        file_error = FileNotFoundError("File not found")
        error_info = handler.classify_exception(file_error)
        assert error_info.category == ErrorCategory.CACHE
        assert error_info.severity == ErrorSeverity.LOW
        
        # Permission error should be high severity
        perm_error = PermissionError("Permission denied")
        error_info = handler.classify_exception(perm_error)
        assert error_info.category == ErrorCategory.CACHE
        assert error_info.severity == ErrorSeverity.HIGH
    
    def test_memory_error_severity(self):
        """Test memory error severity determination."""
        handler = ErrorHandler()
        
        # Memory error should be fatal
        mem_error = MemoryError("Out of memory")
        error_info = handler.classify_exception(mem_error)
        assert error_info.category == ErrorCategory.RESOURCE
        assert error_info.severity == ErrorSeverity.FATAL


class TestGlobalErrorHandler:
    """Test global error handler instance."""
    
    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        assert handler1 is handler2
    
    def test_error_handler_state_persistence(self):
        """Test that error handler maintains state across calls."""
        handler = get_error_handler()
        initial_count = handler.error_stats['total_errors']
        
        # Add an error
        error_info = ErrorInfo(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            message="Test error"
        )
        handler.handle_error(error_info, "test")
        
        # Get handler again and check count persisted
        handler2 = get_error_handler()
        assert handler2.error_stats['total_errors'] == initial_count + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
