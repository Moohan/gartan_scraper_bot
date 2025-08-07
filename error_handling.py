"""
Standardized error handling framework for Gartan Scraper Bot.

Provides consistent exception handling patterns, error classification,
and robust recovery mechanisms across all modules.
"""

import logging
import traceback
import functools
import time
from functools import wraps
from typing import Optional, Dict, Any, Callable, Type, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import sqlite3
import requests
from logging_config import get_logger

logger = get_logger()

class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    LOW = "low"          # Non-critical errors, can continue operation
    MEDIUM = "medium"    # Important errors, may affect functionality
    HIGH = "high"        # Critical errors, may cause operation failure
    FATAL = "fatal"      # Fatal errors, must stop operation

class ErrorCategory(Enum):
    """Error categories for better classification and handling."""
    NETWORK = "network"              # HTTP requests, connectivity issues
    DATABASE = "database"            # SQLite operations, schema issues
    CACHE = "cache"                  # File I/O, cache corruption
    PARSING = "parsing"              # HTML parsing, data extraction
    AUTHENTICATION = "authentication" # Login failures, session issues
    CONFIGURATION = "configuration" # Missing settings, invalid values
    VALIDATION = "validation"       # Data validation failures
    RESOURCE = "resource"           # Memory, disk space, limits
    EXTERNAL = "external"           # Third-party service failures

@dataclass
class ErrorInfo:
    """Structured error information container."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    recoverable: bool = True
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class GartanError(Exception):
    """Base exception class for all Gartan Scraper Bot errors."""
    
    def __init__(self, error_info: ErrorInfo, original_exception: Optional[Exception] = None):
        self.error_info = error_info
        self.original_exception = original_exception
        super().__init__(error_info.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            'category': self.error_info.category.value,
            'severity': self.error_info.severity.value,
            'message': self.error_info.message,
            'details': self.error_info.details,
            'timestamp': self.error_info.timestamp.isoformat(),
            'recoverable': self.error_info.recoverable,
            'retry_count': self.error_info.retry_count,
            'original_exception': str(self.original_exception) if self.original_exception else None
        }

class NetworkError(GartanError):
    """Network-related errors (HTTP requests, connectivity)."""
    pass

class DatabaseError(GartanError):
    """Database-related errors (SQLite operations, schema)."""
    pass

class CacheError(GartanError):
    """Cache-related errors (file I/O, corruption)."""
    pass

class ParsingError(GartanError):
    """Parsing-related errors (HTML parsing, data extraction)."""
    pass

class AuthenticationError(GartanError):
    """Authentication-related errors (login failures, sessions)."""
    pass

class ConfigurationError(GartanError):
    """Configuration-related errors (missing settings, invalid values)."""
    pass

class ValidationError(GartanError):
    """Validation-related errors (data validation failures)."""
    pass

class ResourceError(GartanError):
    """Resource-related errors (memory, disk space, limits)."""
    pass

class ExternalServiceError(GartanError):
    """External service-related errors (third-party failures)."""
    pass

# Exception mapping for automatic classification
EXCEPTION_MAPPING = {
    requests.RequestException: (ErrorCategory.NETWORK, NetworkError),
    requests.ConnectionError: (ErrorCategory.NETWORK, NetworkError),
    requests.Timeout: (ErrorCategory.NETWORK, NetworkError),
    requests.HTTPError: (ErrorCategory.NETWORK, NetworkError),
    ConnectionError: (ErrorCategory.NETWORK, NetworkError),  # Built-in ConnectionError
    sqlite3.Error: (ErrorCategory.DATABASE, DatabaseError),
    sqlite3.OperationalError: (ErrorCategory.DATABASE, DatabaseError),
    sqlite3.IntegrityError: (ErrorCategory.DATABASE, DatabaseError),
    FileNotFoundError: (ErrorCategory.CACHE, CacheError),
    PermissionError: (ErrorCategory.CACHE, CacheError),
    UnicodeDecodeError: (ErrorCategory.CACHE, CacheError),
    ValueError: (ErrorCategory.VALIDATION, ValidationError),
    TypeError: (ErrorCategory.VALIDATION, ValidationError),
    KeyError: (ErrorCategory.PARSING, ParsingError),
    AttributeError: (ErrorCategory.PARSING, ParsingError),
    MemoryError: (ErrorCategory.RESOURCE, ResourceError),
    OSError: (ErrorCategory.RESOURCE, ResourceError),
}

class ErrorHandler:
    """Centralized error handling and recovery management."""
    
    def __init__(self):
        self.error_stats = {
            'total_errors': 0,
            'errors_by_category': {cat.value: 0 for cat in ErrorCategory},
            'errors_by_severity': {sev.value: 0 for sev in ErrorSeverity},
            'recoverable_errors': 0,
            'fatal_errors': 0
        }
    
    def classify_exception(self, exception: Exception) -> ErrorInfo:
        """Automatically classify an exception into structured error info."""
        exception_type = type(exception)
        
        # Check for direct mapping
        if exception_type in EXCEPTION_MAPPING:
            category, _ = EXCEPTION_MAPPING[exception_type]
        else:
            # Check for inheritance
            category = ErrorCategory.EXTERNAL
            for exc_type, (cat, _) in EXCEPTION_MAPPING.items():
                if isinstance(exception, exc_type):
                    category = cat
                    break
        
        # Determine severity based on category and exception details
        severity = self._determine_severity(category, exception)
        
        # Create error info
        error_info = ErrorInfo(
            category=category,
            severity=severity,
            message=str(exception),
            details={
                'exception_type': exception_type.__name__,
                'traceback': traceback.format_exc()
            },
            recoverable=severity != ErrorSeverity.FATAL
        )
        
        return error_info
    
    def _determine_severity(self, category: ErrorCategory, exception: Exception) -> ErrorSeverity:
        """Determine error severity based on category and exception details."""
        # Network errors
        if category == ErrorCategory.NETWORK:
            if isinstance(exception, (requests.ConnectionError, requests.Timeout, ConnectionError)):
                return ErrorSeverity.MEDIUM
            elif isinstance(exception, requests.HTTPError):
                if hasattr(exception, 'response') and exception.response:
                    status_code = exception.response.status_code
                    if status_code >= 500:
                        return ErrorSeverity.HIGH
                    elif status_code >= 400:
                        return ErrorSeverity.MEDIUM
                return ErrorSeverity.MEDIUM
            return ErrorSeverity.LOW
        
        # Database errors
        elif category == ErrorCategory.DATABASE:
            if isinstance(exception, sqlite3.OperationalError):
                error_msg = str(exception).lower()
                if 'database is locked' in error_msg:
                    return ErrorSeverity.MEDIUM
                elif 'no such table' in error_msg or 'no such column' in error_msg:
                    return ErrorSeverity.HIGH
                return ErrorSeverity.MEDIUM
            elif isinstance(exception, sqlite3.IntegrityError):
                return ErrorSeverity.LOW  # Usually constraint violations
            return ErrorSeverity.MEDIUM
        
        # Cache errors
        elif category == ErrorCategory.CACHE:
            if isinstance(exception, PermissionError):
                return ErrorSeverity.HIGH
            elif isinstance(exception, (FileNotFoundError, UnicodeDecodeError)):
                return ErrorSeverity.LOW
            return ErrorSeverity.MEDIUM
        
        # Authentication errors
        elif category == ErrorCategory.AUTHENTICATION:
            return ErrorSeverity.HIGH  # Always serious
        
        # Configuration errors
        elif category == ErrorCategory.CONFIGURATION:
            return ErrorSeverity.FATAL  # Usually fatal
        
        # Resource errors
        elif category == ErrorCategory.RESOURCE:
            if isinstance(exception, MemoryError):
                return ErrorSeverity.FATAL
            return ErrorSeverity.HIGH
        
        # Default
        return ErrorSeverity.MEDIUM
    
    def handle_error(self, error_info: ErrorInfo, context: str = "") -> bool:
        """
        Handle an error according to its severity and category.
        Returns True if operation should continue, False if it should stop.
        """
        self._update_stats(error_info)
        
        # Log the error
        self._log_error(error_info, context)
        
        # Handle based on severity
        if error_info.severity == ErrorSeverity.FATAL:
            logger.error(f"FATAL ERROR in {context}: {error_info.message}")
            return False
        
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH severity error in {context}: {error_info.message}")
            # For high severity, stop if not recoverable
            return error_info.recoverable
        
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM severity error in {context}: {error_info.message}")
            return True
        
        else:  # LOW severity
            logger.debug(f"LOW severity error in {context}: {error_info.message}")
            return True
    
    def handle_error_legacy(self, category: ErrorCategory, severity: ErrorSeverity, 
                          message: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Legacy interface for handle_error - creates ErrorInfo internally."""
        error_info = ErrorInfo(
            category=category,
            severity=severity,
            message=message,
            details=details or {}
        )
        return self.handle_error(error_info)
    
    def _update_stats(self, error_info: ErrorInfo):
        """Update error statistics."""
        self.error_stats['total_errors'] += 1
        self.error_stats['errors_by_category'][error_info.category.value] += 1
        self.error_stats['errors_by_severity'][error_info.severity.value] += 1
        
        if error_info.recoverable:
            self.error_stats['recoverable_errors'] += 1
        
        if error_info.severity == ErrorSeverity.FATAL:
            self.error_stats['fatal_errors'] += 1
    
    def _log_error(self, error_info: ErrorInfo, context: str):
        """Log error with appropriate level and format."""
        log_data = {
            'context': context,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'message': error_info.message,
            'recoverable': error_info.recoverable,
            'retry_count': error_info.retry_count
        }
        
        if error_info.details:
            log_data.update(error_info.details)
        
        # Choose log level based on severity
        if error_info.severity == ErrorSeverity.FATAL:
            logger.error(f"ERROR_HANDLER: {log_data}")
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(f"ERROR_HANDLER: {log_data}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"ERROR_HANDLER: {log_data}")
        else:
            logger.debug(f"ERROR_HANDLER: {log_data}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        return self.error_stats.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics (alias for get_stats)."""
        stats = self.error_stats.copy()
        stats['by_category'] = self.error_stats['errors_by_category']
        stats['by_severity'] = self.error_stats['errors_by_severity']
        return stats
    
    def with_retry(self, func: Callable, max_retries: int = 3, 
                   delay: float = 1.0, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_info = self.classify_exception(e)
                
                # If this is the last attempt or a fatal error, re-raise
                if attempt == max_retries or error_info.severity == ErrorSeverity.FATAL:
                    raise
                
                # Log retry attempt
                logger.warning(f"Retry {attempt + 1}/{max_retries} after error: {str(e)}")
                
                # Wait before retry
                if delay > 0:
                    time.sleep(delay)
        
        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

# Global error handler instance
_error_handler = ErrorHandler()

def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler

def handle_errors(
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    recoverable: bool = True,
    max_retries: int = 3,
    context: str = ""
):
    """
    Decorator for automatic error handling with retry logic.
    
    Args:
        category: Override error category classification
        severity: Override error severity classification  
        recoverable: Whether errors should be treated as recoverable
        max_retries: Maximum number of retry attempts
        context: Context string for logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    # Classify the error
                    error_info = error_handler.classify_exception(e)
                    
                    # Override classification if specified
                    if category:
                        error_info.category = category
                    if severity:
                        error_info.severity = severity
                    
                    error_info.recoverable = recoverable
                    error_info.retry_count = retry_count
                    error_info.max_retries = max_retries
                    
                    # Handle the error
                    func_context = context or f"{func.__module__}.{func.__name__}"
                    should_continue = error_handler.handle_error(error_info, func_context)
                    
                    # Decide whether to retry
                    if (error_info.recoverable and 
                        retry_count < max_retries and 
                        error_info.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]):
                        retry_count += 1
                        logger.debug(f"Retrying {func_context}, attempt {retry_count}/{max_retries}")
                        continue
                    
                    # Create appropriate Gartan exception
                    gartan_exception = _create_gartan_exception(error_info, e)
                    
                    if should_continue and error_info.recoverable:
                        # Return None or appropriate default value for recoverable errors
                        logger.info(f"Recovered from error in {func_context}, continuing operation")
                        return None
                    else:
                        # Re-raise as Gartan exception
                        raise gartan_exception
            
            # Should never reach here
            return None
        
        return wrapper
    return decorator

def _create_gartan_exception(error_info: ErrorInfo, original_exception: Exception) -> GartanError:
    """Create appropriate Gartan exception based on error category."""
    exception_classes = {
        ErrorCategory.NETWORK: NetworkError,
        ErrorCategory.DATABASE: DatabaseError,
        ErrorCategory.CACHE: CacheError,
        ErrorCategory.PARSING: ParsingError,
        ErrorCategory.AUTHENTICATION: AuthenticationError,
        ErrorCategory.CONFIGURATION: ConfigurationError,
        ErrorCategory.VALIDATION: ValidationError,
        ErrorCategory.RESOURCE: ResourceError,
        ErrorCategory.EXTERNAL: ExternalServiceError,
    }
    
    exception_class = exception_classes.get(error_info.category, GartanError)
    return exception_class(error_info, original_exception)

def safe_execute(
    func: Callable,
    *args,
    default_return=None,
    context: str = "",
    **kwargs
) -> Any:
    """
    Safely execute a function with automatic error handling.
    Returns default_return on any error.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler = get_error_handler()
        error_info = error_handler.classify_exception(e)
        error_handler.handle_error(error_info, context or f"safe_execute:{func.__name__}")
        return default_return

def handle_exceptions(error_category: ErrorCategory = ErrorCategory.EXTERNAL,
                     retry_max: int = 0, retry_delay: float = 1.0):
    """Decorator for automatic exception handling with optional retry."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_error_handler()
            
            for attempt in range(retry_max + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_info = handler.classify_exception(e)
                    error_info.category = error_category  # Override category if specified
                    
                    # Log the error
                    handler.handle_error(error_info)
                    
                    # If this is the last attempt or a fatal error, raise a structured error
                    if attempt == retry_max or error_info.severity == ErrorSeverity.FATAL:
                        # Create appropriate exception and raise
                        structured_exception = _create_gartan_exception(error_info, e)
                        raise structured_exception
                    
                    # Wait before retry
                    if retry_delay > 0:
                        time.sleep(retry_delay)
            
            # Should never reach here
            raise GartanError(
                ErrorInfo(
                    category=ErrorCategory.EXTERNAL,
                    severity=ErrorSeverity.HIGH,
                    message="Maximum retries exceeded",
                    details={"max_retries": retry_max}
                )
            )
        
        return wrapper
    return decorator
