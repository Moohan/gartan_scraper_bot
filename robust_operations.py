"""
Robust Database Operations with Integrated Error Handling and Logging.

Enhances database operations with automatic retry, connection recovery,
and comprehensive error handling.
"""

import sqlite3
import time
import threading
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from contextlib import contextmanager
from dataclasses import dataclass

from database_manager import DatabaseManager, get_database_manager
from error_logging_integration import robust_operation, get_integrated_logger, OperationContext
from error_handling import ErrorCategory, ErrorSeverity, DatabaseError, ErrorInfo
from logging_config import get_logger

logger = get_logger()


@dataclass
class ConnectionHealth:
    """Database connection health information."""
    is_healthy: bool
    last_check: float
    error_count: int
    last_error: Optional[str] = None


class RobustDatabaseManager:
    """
    Enhanced database manager with robust error handling and automatic recovery.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.database_manager = get_database_manager(db_path)
        self.integrated_logger = get_integrated_logger()
        self.connection_health = ConnectionHealth(
            is_healthy=True,
            last_check=time.time(),
            error_count=0
        )
        self._lock = threading.Lock()
        
    @robust_operation(
        operation_name="database_execute",
        component="database",
        max_retries=3,
        retry_delay=0.5
    )
    def execute_query(
        self,
        query: str,
        params: Optional[Union[Tuple, Dict]] = None,
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Any:
        """
        Execute a database query with robust error handling.
        """
        with self._lock:
            try:
                with self.database_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    # Handle different return types
                    if fetch_one:
                        return cursor.fetchone()
                    elif fetch_all:
                        return cursor.fetchall()
                    else:
                        return cursor.rowcount
                        
            except sqlite3.Error as e:
                self._update_connection_health(False, str(e))
                raise DatabaseError(
                    ErrorInfo(
                        category=ErrorCategory.DATABASE,
                        severity=ErrorSeverity.MEDIUM,
                        message=f"Database query failed: {str(e)}",
                        details={
                            'query': query[:100] + "..." if len(query) > 100 else query,
                            'params': str(params) if params else None,
                            'database_path': self.db_path
                        }
                    ),
                    original_exception=e
                )
    
    @robust_operation(
        operation_name="database_batch_insert",
        component="database",
        max_retries=2,
        retry_delay=1.0
    )
    def batch_insert(
        self,
        table: str,
        data: List[Dict[str, Any]],
        on_conflict: str = "IGNORE"
    ) -> int:
        """
        Perform batch insert with robust error handling.
        """
        if not data:
            return 0
            
        # Get column names from first record
        columns = list(data[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        column_names = ", ".join(columns)
        
        query = f"""
            INSERT OR {on_conflict} INTO {table} ({column_names})
            VALUES ({placeholders})
        """
        
        # Convert data to tuples
        values = [tuple(record[col] for col in columns) for record in data]
        
        context = OperationContext(
            operation_name=f"batch_insert_{table}",
            component="database",
            metadata={
                'table': table,
                'record_count': len(data),
                'on_conflict': on_conflict
            }
        )
        
        with self.integrated_logger.operation_context(context):
            try:
                with self.database_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, values)
                    return cursor.rowcount
                    
            except sqlite3.Error as e:
                self._update_connection_health(False, str(e))
                raise DatabaseError(
                    ErrorInfo(
                        category=ErrorCategory.DATABASE,
                        severity=ErrorSeverity.HIGH,
                        message=f"Batch insert failed for table {table}: {str(e)}",
                        details={
                            'table': table,
                            'record_count': len(data),
                            'database_path': self.db_path,
                            'sample_record': data[0] if data else None
                        }
                    ),
                    original_exception=e
                )
    
    @robust_operation(
        operation_name="database_transaction",
        component="database",
        max_retries=3,
        retry_delay=1.0
    )
    def execute_transaction(self, operations: List[Callable[[sqlite3.Cursor], None]]) -> bool:
        """
        Execute multiple operations in a single transaction with error handling.
        """
        context = OperationContext(
            operation_name="database_transaction",
            component="database",
            metadata={'operation_count': len(operations)}
        )
        
        with self.integrated_logger.operation_context(context):
            try:
                with self.database_manager.transaction() as conn:
                    cursor = conn.cursor()
                    for operation in operations:
                        operation(cursor)
                    return True
                    
            except sqlite3.Error as e:
                self._update_connection_health(False, str(e))
                raise DatabaseError(
                    ErrorInfo(
                        category=ErrorCategory.DATABASE,
                        severity=ErrorSeverity.HIGH,
                        message=f"Transaction failed: {str(e)}",
                        details={
                            'operation_count': len(operations),
                            'database_path': self.db_path
                        }
                    ),
                    original_exception=e
                )
    
    def check_connection_health(self) -> bool:
        """
        Check database connection health.
        """
        try:
            result = self.execute_query(
                "SELECT 1",
                fetch_one=True
            )
            
            self._update_connection_health(True)
            return result is not None
            
        except Exception as e:
            self._update_connection_health(False, str(e))
            return False
    
    def _update_connection_health(self, is_healthy: bool, error_message: Optional[str] = None):
        """Update connection health status."""
        with self._lock:
            self.connection_health.is_healthy = is_healthy
            self.connection_health.last_check = time.time()
            
            if not is_healthy:
                self.connection_health.error_count += 1
                self.connection_health.last_error = error_message
                
                logger.warning(
                    f"Database connection health degraded: {error_message}",
                    extra={
                        'component': 'database',
                        'database_path': self.db_path,
                        'error_count': self.connection_health.error_count,
                        'health_status': 'degraded'
                    }
                )
            else:
                # Reset error count on successful connection
                if self.connection_health.error_count > 0:
                    logger.info(
                        "Database connection health restored",
                        extra={
                            'component': 'database',
                            'database_path': self.db_path,
                            'previous_error_count': self.connection_health.error_count,
                            'health_status': 'healthy'
                        }
                    )
                self.connection_health.error_count = 0
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get database health status for monitoring."""
        return {
            'is_healthy': self.connection_health.is_healthy,
            'last_check_age_seconds': time.time() - self.connection_health.last_check,
            'error_count': self.connection_health.error_count,
            'last_error': self.connection_health.last_error,
            'database_path': self.db_path,
            'pool_status': self.database_manager.get_pool_status()
        }


class SmartCacheManager:
    """
    Cache management with integrated error handling and health monitoring.
    """
    
    def __init__(self, cache_dir: str = "_cache"):
        self.cache_dir = cache_dir
        self.integrated_logger = get_integrated_logger()
        
    @robust_operation(
        operation_name="cache_read",
        component="cache",
        max_retries=2,
        retry_delay=0.1
    )
    def read_cache_file(self, file_path: str, encoding: str = "utf-8") -> Optional[str]:
        """
        Read cache file with robust error handling.
        """
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
                
            logger.debug(
                f"Cache hit: {file_path}",
                extra={
                    'component': 'cache',
                    'file_path': file_path,
                    'content_size': len(content),
                    'cache_hit': True
                }
            )
            
            return content
            
        except (FileNotFoundError, UnicodeDecodeError, PermissionError) as e:
            logger.debug(
                f"Cache miss or error: {file_path} - {str(e)}",
                extra={
                    'component': 'cache',
                    'file_path': file_path,
                    'cache_hit': False,
                    'error': str(e)
                }
            )
            return None
    
    @robust_operation(
        operation_name="cache_write",
        component="cache",
        max_retries=3,
        retry_delay=0.5
    )
    def write_cache_file(
        self,
        file_path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> bool:
        """
        Write cache file with robust error handling.
        """
        context = OperationContext(
            operation_name="cache_write",
            component="cache",
            metadata={
                'file_path': file_path,
                'content_size': len(content),
                'encoding': encoding
            }
        )
        
        with self.integrated_logger.operation_context(context):
            try:
                # Create directories if needed
                if create_dirs:
                    import os
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, "w", encoding=encoding) as f:
                    f.write(content)
                
                logger.debug(
                    f"Cache written: {file_path}",
                    extra={
                        'component': 'cache',
                        'file_path': file_path,
                        'content_size': len(content),
                        'operation': 'write'
                    }
                )
                
                return True
                
            except (PermissionError, OSError, UnicodeEncodeError) as e:
                logger.error(
                    f"Cache write failed: {file_path} - {str(e)}",
                    extra={
                        'component': 'cache',
                        'file_path': file_path,
                        'content_size': len(content),
                        'operation': 'write',
                        'error': str(e)
                    }
                )
                return False


# Global instances for easy access
_robust_db_managers: Dict[str, RobustDatabaseManager] = {}
_cache_manager = SmartCacheManager()

def get_robust_database_manager(db_path: str) -> RobustDatabaseManager:
    """Get or create a robust database manager for the given path."""
    if db_path not in _robust_db_managers:
        _robust_db_managers[db_path] = RobustDatabaseManager(db_path)
    return _robust_db_managers[db_path]

def get_cache_manager() -> SmartCacheManager:
    """Get the global cache manager."""
    return _cache_manager
