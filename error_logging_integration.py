"""
Error Handling & Logging Integration for Phase 2 Improvements.

Integrates existing error handling and enhanced logging systems with
practical improvements for robustness and monitoring.
"""

import logging
import time
import functools
from typing import Any, Callable, Dict, Optional, Type, Union
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from error_handling import (
    ErrorHandler, ErrorInfo, ErrorCategory, ErrorSeverity,
    get_error_handler, handle_errors, GartanError
)
from enhanced_logging import StructuredFormatter, LogContext, PerformanceMetrics
from logging_config import get_logger
from unified_config import get_config

logger = get_logger()
config = get_config()


@dataclass
class OperationContext:
    """Comprehensive operation context for error handling and logging."""
    operation_name: str
    component: str
    start_time: Optional[datetime] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class IntegratedErrorLogger:
    """
    Integrated error handling and logging system that combines
    structured logging with robust error recovery.
    """
    
    def __init__(self):
        self.error_handler = get_error_handler()
        self.operation_stack = []
        self._error_counts = {}
        
    @contextmanager
    def operation_context(self, context: OperationContext):
        """Context manager for tracking operations with integrated error handling."""
        self.operation_stack.append(context)
        start_time = time.time()
        
        try:
            logger.info(
                f"Starting operation: {context.operation_name}",
                extra={
                    'operation': context.operation_name,
                    'component': context.component,
                    'context': context.__dict__
                }
            )
            
            yield context
            
            # Success metrics
            duration = time.time() - start_time
            logger.info(
                f"Completed operation: {context.operation_name} in {duration:.2f}s",
                extra={
                    'operation': context.operation_name,
                    'component': context.component,
                    'duration': duration,
                    'success': True
                }
            )
            
        except Exception as e:
            # Integrated error handling
            duration = time.time() - start_time
            error_info = self.error_handler.classify_exception(e)
            
            # Enhanced error context
            error_info.details = error_info.details or {}
            error_info.details.update({
                'operation': context.operation_name,
                'component': context.component,
                'duration': duration,
                'operation_metadata': context.metadata
            })
            
            # Track error patterns
            error_key = f"{context.component}:{error_info.category.value}"
            self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
            
            # Enhanced logging with full context
            logger.error(
                f"Operation failed: {context.operation_name} - {error_info.message}",
                extra={
                    'operation': context.operation_name,
                    'component': context.component,
                    'error_category': error_info.category.value,
                    'error_severity': error_info.severity.value,
                    'duration': duration,
                    'error_count': self._error_counts[error_key],
                    'success': False,
                    'error_details': error_info.details
                },
                exc_info=True
            )
            
            # Handle based on severity
            should_continue = self.error_handler.handle_error(error_info, context.operation_name)
            
            if not should_continue:
                raise
                
        finally:
            if self.operation_stack:
                self.operation_stack.pop()
    
    def safe_operation(
        self,
        operation_name: str,
        component: str,
        func: Callable,
        *args,
        default_return=None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ) -> Any:
        """
        Execute an operation with integrated error handling, retries, and logging.
        """
        context = OperationContext(
            operation_name=operation_name,
            component=component,
            metadata={'args_count': len(args), 'kwargs_count': len(kwargs)}
        )
        
        with self.operation_context(context):
            # Use retry logic with exponential backoff
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    error_info = self.error_handler.classify_exception(e)
                    
                    # On final attempt or fatal error, raise
                    if attempt == max_retries or error_info.severity == ErrorSeverity.FATAL:
                        raise
                    
                    # Log retry attempt
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {operation_name}: {str(e)}",
                        extra={
                            'operation': operation_name,
                            'component': component,
                            'attempt': attempt + 1,
                            'max_retries': max_retries
                        }
                    )
                    
                    # Exponential backoff
                    sleep_time = retry_delay * (2 ** attempt)
                    time.sleep(min(sleep_time, 30))  # Cap at 30 seconds
            
            return default_return


def robust_operation(
    operation_name: str,
    component: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    default_return=None,
    log_performance: bool = True
):
    """
    Decorator for robust operations with integrated error handling and logging.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            integrated_logger = IntegratedErrorLogger()
            
            if log_performance:
                # Track performance
                start_time = time.time()
                
            try:
                result = integrated_logger.safe_operation(
                    operation_name,
                    component,
                    func,
                    *args,
                    default_return=default_return,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                    **kwargs
                )
                
                if log_performance:
                    duration = time.time() - start_time
                    logger.debug(
                        f"Performance: {operation_name} completed in {duration:.3f}s",
                        extra={
                            'operation': operation_name,
                            'component': component,
                            'duration': duration,
                            'performance_tracked': True
                        }
                    )
                
                return result
                
            except Exception as e:
                if log_performance:
                    duration = time.time() - start_time
                    logger.error(
                        f"Performance: {operation_name} failed after {duration:.3f}s",
                        extra={
                            'operation': operation_name,
                            'component': component,
                            'duration': duration,
                            'performance_tracked': True,
                            'failed': True
                        }
                    )
                raise
        
        return wrapper
    return decorator
    return decorator


class HealthMonitor:
    """
    System health monitoring with integrated error tracking and logging.
    """
    
    def __init__(self):
        self.error_handler = get_error_handler()
        self.start_time = datetime.now()
        self.health_checks = {}
        
    def add_health_check(self, name: str, check_func: Callable[[], bool]):
        """Add a health check function."""
        self.health_checks[name] = check_func
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        status = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'error_statistics': self.error_handler.get_statistics(),
            'health_checks': {},
            'overall_status': 'healthy'
        }
        
        # Run health checks
        failed_checks = 0
        for check_name, check_func in self.health_checks.items():
            try:
                check_result = check_func()
                status['health_checks'][check_name] = {
                    'status': 'pass' if check_result else 'fail',
                    'checked_at': datetime.now().isoformat()
                }
                if not check_result:
                    failed_checks += 1
                    
            except Exception as e:
                status['health_checks'][check_name] = {
                    'status': 'error',
                    'error': str(e),
                    'checked_at': datetime.now().isoformat()
                }
                failed_checks += 1
        
        # Determine overall status
        if failed_checks > 0:
            status['overall_status'] = 'degraded' if failed_checks < len(self.health_checks) else 'unhealthy'
        
        # Check error rates
        error_stats = status['error_statistics']
        if error_stats.get('fatal_errors', 0) > 0:
            status['overall_status'] = 'critical'
        elif error_stats.get('total_errors', 0) > 10:  # Configurable threshold
            status['overall_status'] = 'degraded'
        
        return status
    
    def log_health_status(self):
        """Log current health status."""
        health_status = self.get_health_status()
        
        if health_status['overall_status'] == 'healthy':
            logger.info(f"System health: {health_status['overall_status']}", extra=health_status)
        elif health_status['overall_status'] in ['degraded', 'unhealthy']:
            logger.warning(f"System health: {health_status['overall_status']}", extra=health_status)
        else:  # critical
            logger.error(f"System health: {health_status['overall_status']}", extra=health_status)


# Global instances
_integrated_logger = IntegratedErrorLogger()
_health_monitor = HealthMonitor()

def get_integrated_logger() -> IntegratedErrorLogger:
    """Get the global integrated error logger."""
    return _integrated_logger

def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor."""
    return _health_monitor
