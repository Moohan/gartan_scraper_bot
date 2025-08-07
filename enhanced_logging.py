"""
Enhanced logging system for Gartan Scraper Bot.

Provides structured logging with performance monitoring, context tracking,
and intelligent log management.
"""

import logging
import logging.handlers
import json
import time
import threading
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
import sys
import traceback
from collections import defaultdict, deque

from unified_config import GartanConfig, LogLevel, get_config
from error_handling import ErrorInfo, ErrorCategory, ErrorSeverity

@dataclass
class LogContext:
    """Context information for structured logging."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMetrics:
    """Performance metrics for logging."""
    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None

class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""
    
    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add context if available
        if self.include_context and hasattr(record, 'context'):
            log_entry["context"] = record.context.__dict__
        
        # Add performance metrics if available
        if hasattr(record, 'performance'):
            log_entry["performance"] = record.performance.__dict__
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage',
                          'context', 'performance'):
                if not key.startswith('_'):
                    log_entry["extra"] = log_entry.get("extra", {})
                    log_entry["extra"][key] = value
        
        return json.dumps(log_entry, default=str)

class PerformanceTracker:
    """Tracks performance metrics for logging."""
    
    def __init__(self):
        self._active_operations: Dict[str, float] = {}
        self._metrics_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
    
    def start_operation(self, operation: str, operation_id: Optional[str] = None) -> str:
        """Start tracking an operation."""
        if operation_id is None:
            operation_id = f"{operation}_{int(time.time() * 1000)}"
        
        with self._lock:
            self._active_operations[operation_id] = time.time()
        
        return operation_id
    
    def end_operation(self, operation_id: str, operation: str, 
                     success: bool = True, error_message: Optional[str] = None) -> PerformanceMetrics:
        """End tracking an operation and return metrics."""
        end_time = time.time()
        
        with self._lock:
            start_time = self._active_operations.pop(operation_id, end_time)
        
        duration = end_time - start_time
        
        # Try to get memory usage
        memory_usage_mb = None
        try:
            import psutil
            process = psutil.Process()
            memory_usage_mb = process.memory_info().rss / 1024 / 1024
        except ImportError:
            pass
        
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            memory_usage_mb=memory_usage_mb,
            success=success,
            error_message=error_message
        )
        
        with self._lock:
            self._metrics_history.append(metrics)
        
        return metrics
    
    def get_recent_metrics(self, count: int = 10) -> List[PerformanceMetrics]:
        """Get recent performance metrics."""
        with self._lock:
            return list(self._metrics_history)[-count:]

class LogManager:
    """Enhanced log manager with structured logging and performance tracking."""
    
    def __init__(self, config: Optional[GartanConfig] = None):
        self.config = config or get_config()
        self.performance_tracker = PerformanceTracker()
        self._context_stack: List[LogContext] = []
        self._lock = threading.Lock()
        self._loggers: Dict[str, logging.Logger] = {}
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up enhanced logging configuration."""
        # Create logs directory if needed
        log_path = Path(self.config.logging.file_path)
        log_path.parent.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.config.logging.file_path,
            maxBytes=self.config.logging.max_file_size_mb * 1024 * 1024,
            backupCount=self.config.logging.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, self.config.logging.file_level.value))
        file_handler.setFormatter(StructuredFormatter(include_context=True))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.config.logging.console_level.value))
        console_handler.setFormatter(
            logging.Formatter(self.config.logging.format_string)
        )
        
        # Add handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger instance."""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        return self._loggers[name]
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for structured logging context."""
        # Put all kwargs into additional_data to avoid parameter conflicts
        context = LogContext(additional_data=kwargs)
        
        with self._lock:
            self._context_stack.append(context)
        
        try:
            yield context
        finally:
            with self._lock:
                if self._context_stack:
                    self._context_stack.pop()
    
    def _get_current_context(self) -> Optional[LogContext]:
        """Get the current logging context."""
        with self._lock:
            return self._context_stack[-1] if self._context_stack else None
    
    def log_with_context(self, level: int, message: str, logger_name: str = "gartan",
                        extra_context: Optional[Dict[str, Any]] = None,
                        performance: Optional[PerformanceMetrics] = None):
        """Log message with current context."""
        logger = self.get_logger(logger_name)
        
        # Create log record
        record = logger.makeRecord(
            name=logger_name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # Add context
        current_context = self._get_current_context()
        if current_context:
            context_dict = current_context.__dict__.copy()
            if extra_context:
                context_dict["additional_data"].update(extra_context)
            record.context = LogContext(**context_dict)
        elif extra_context:
            record.context = LogContext(additional_data=extra_context)
        
        # Add performance metrics
        if performance:
            record.performance = performance
        
        logger.handle(record)
    
    @contextmanager
    def track_performance(self, operation: str, logger_name: str = "gartan.performance",
                         log_start: bool = True, log_end: bool = True):
        """Context manager for performance tracking with logging."""
        operation_id = self.performance_tracker.start_operation(operation)
        
        if log_start:
            self.log_with_context(
                logging.INFO,
                f"Starting operation: {operation}",
                logger_name,
                {"operation_id": operation_id, "operation": operation}
            )
        
        start_time = time.time()
        success = True
        error_message = None
        
        try:
            yield operation_id
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            metrics = self.performance_tracker.end_operation(
                operation_id, operation, success, error_message
            )
            
            if log_end:
                level = logging.INFO if success else logging.ERROR
                message = f"Completed operation: {operation} (duration: {metrics.duration:.3f}s)"
                if not success:
                    message += f" - Error: {error_message}"
                
                self.log_with_context(
                    level,
                    message,
                    logger_name,
                    {
                        "operation_id": operation_id,
                        "operation": operation,
                        "success": success
                    },
                    performance=metrics
                )

# Global log manager instance
_log_manager: Optional[LogManager] = None

def get_log_manager() -> LogManager:
    """Get the global log manager instance."""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager

def setup_logging(config: Optional[GartanConfig] = None):
    """Set up enhanced logging system."""
    global _log_manager
    _log_manager = LogManager(config)

# Convenience functions
def get_logger(name: str = "gartan") -> logging.Logger:
    """Get a configured logger."""
    return get_log_manager().get_logger(name)

@contextmanager
def log_context(**kwargs):
    """Context manager for logging context."""
    with get_log_manager().context(**kwargs):
        yield

@contextmanager
def track_performance(operation: str, logger_name: str = "gartan.performance"):
    """Context manager for performance tracking."""
    with get_log_manager().track_performance(operation, logger_name):
        yield

def log_with_performance(operation: str):
    """Decorator for automatic performance logging."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with track_performance(f"{func.__module__}.{func.__name__}_{operation}"):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Legacy compatibility functions
def log_debug(message: str, **kwargs):
    """Legacy debug logging function."""
    logger = get_logger()
    logger.debug(message, extra=kwargs)

def log_info(message: str, **kwargs):
    """Legacy info logging function."""
    logger = get_logger()
    logger.info(message, extra=kwargs)

def log_warning(message: str, **kwargs):
    """Legacy warning logging function."""
    logger = get_logger()
    logger.warning(message, extra=kwargs)

def log_error(message: str, **kwargs):
    """Legacy error logging function."""
    logger = get_logger()
    logger.error(message, extra=kwargs)

# Initialize logging on import
setup_logging()
