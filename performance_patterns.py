"""
Performance Pattern Analysis and Common Utilities

This module extracts common patterns identified across the codebase for Phase 3 improvements.
Provides centralized utility functions for performance optimization and pattern extraction.
"""

import time
import functools
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple, Iterator
from datetime import datetime, timedelta
from contextlib import contextmanager
from dataclasses import dataclass
from logging_config import get_logger
from error_handling import ErrorCategory, ErrorHandler

logger = get_logger()
error_handler = ErrorHandler()

# Common Performance Patterns Identified
# =====================================

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    items_processed: int = 0
    errors_encountered: int = 0
    throughput: Optional[float] = None  # items/second
    
    def finalize(self) -> None:
        """Calculate final metrics."""
        if self.end_time and self.start_time:
            self.duration = self.end_time - self.start_time
            if self.items_processed > 0 and self.duration > 0:
                self.throughput = self.items_processed / self.duration


class PerformanceProfiler:
    """Centralized performance profiling and monitoring."""
    
    def __init__(self):
        self._metrics: Dict[str, List[PerformanceMetrics]] = {}
        self._active_operations: Dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def profile_operation(self, operation_name: str, items_count: int = 0):
        """Context manager for profiling operations."""
        import psutil
        import os
        
        with self._lock:
            start_time = time.time()
            process = psutil.Process(os.getpid())
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                items_processed=items_count,
                memory_usage_mb=start_memory
            )
            self._active_operations[operation_name] = metrics
        
        try:
            yield metrics
        except Exception as e:
            with self._lock:
                metrics.errors_encountered += 1
            # Create ErrorInfo for proper error handling
            from error_handling import ErrorInfo, ErrorSeverity
            error_info = ErrorInfo(
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.MEDIUM,
                message=str(e)
            )
            error_handler.handle_error(error_info, f"Performance profiling: {operation_name}")
            raise
        finally:
            with self._lock:
                end_time = time.time()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                metrics.end_time = end_time
                metrics.memory_usage_mb = end_memory - start_memory
                metrics.finalize()
                
                # Store completed metrics
                if operation_name not in self._metrics:
                    self._metrics[operation_name] = []
                self._metrics[operation_name].append(metrics)
                
                # Remove from active operations
                if operation_name in self._active_operations:
                    del self._active_operations[operation_name]
                
                logger.debug(f"Operation '{operation_name}' completed in {metrics.duration:.3f}s, "
                           f"memory delta: {metrics.memory_usage_mb:.1f}MB")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance metrics."""
        with self._lock:
            summary = {}
            for operation, metrics_list in self._metrics.items():
                if not metrics_list:
                    continue
                
                durations = [m.duration for m in metrics_list if m.duration]
                throughputs = [m.throughput for m in metrics_list if m.throughput]
                memory_usages = [m.memory_usage_mb for m in metrics_list if m.memory_usage_mb]
                
                summary[operation] = {
                    'count': len(metrics_list),
                    'avg_duration': sum(durations) / len(durations) if durations else 0,
                    'min_duration': min(durations) if durations else 0,
                    'max_duration': max(durations) if durations else 0,
                    'avg_throughput': sum(throughputs) / len(throughputs) if throughputs else 0,
                    'avg_memory_delta': sum(memory_usages) / len(memory_usages) if memory_usages else 0,
                    'total_errors': sum(m.errors_encountered for m in metrics_list)
                }
            
            return summary


# Global performance profiler instance
_performance_profiler = PerformanceProfiler()

def get_profiler() -> PerformanceProfiler:
    """Get the global performance profiler."""
    return _performance_profiler


# Common Pattern: Batch Processing
# ================================

class BatchProcessor:
    """Generic batch processor for common batch operations."""
    
    def __init__(self, batch_size: int = 50, max_workers: int = 3):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.profiler = get_profiler()
    
    def process_in_batches(self, 
                          items: List[Any], 
                          processor_func: Callable[[List[Any]], Any],
                          operation_name: str = "batch_processing") -> List[Any]:
        """Process items in batches with performance monitoring."""
        
        with self.profiler.profile_operation(operation_name, len(items)) as metrics:
            results = []
            total_batches = (len(items) + self.batch_size - 1) // self.batch_size
            
            for i in range(0, len(items), self.batch_size):
                batch = items[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                
                try:
                    with self.profiler.profile_operation(f"{operation_name}_batch_{batch_num}", 
                                                       len(batch)):
                        result = processor_func(batch)
                        results.append(result)
                        
                        logger.debug(f"Processed batch {batch_num}/{total_batches} "
                                   f"({len(batch)} items)")
                        
                except Exception as e:
                    metrics.errors_encountered += 1
                    logger.error(f"Error processing batch {batch_num}: {e}")
                    # Continue with next batch
                    continue
            
            return results


# Common Pattern: Cache Operations
# ================================

class CacheOperations:
    """Optimized cache operations with performance tracking."""
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.profiler = get_profiler()
    
    def batch_cache_operation(self, 
                             dates: List[str], 
                             operation: str,
                             cache_minutes_map: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Perform batch cache operations with monitoring."""
        
        operation_name = f"cache_{operation}_batch"
        with self.profiler.profile_operation(operation_name, len(dates)) as metrics:
            
            if operation == "check":
                cache_minutes = cache_minutes_map or {}
                return self.cache_manager.batch_cache_check(dates, 
                                                          cache_minutes.get(dates[0], 15))
            
            elif operation == "warm":
                if not cache_minutes_map:
                    raise ValueError("cache_minutes_map required for warm operation")
                return self.cache_manager.warm_cache_batch(None, dates, cache_minutes_map)
            
            elif operation == "cleanup":
                removed = self.cache_manager.cleanup_expired_cache(max_age_days=30)
                metrics.items_processed = removed
                return {"removed_files": removed}
            
            else:
                raise ValueError(f"Unknown cache operation: {operation}")


# Common Pattern: Database Operations
# ===================================

class DatabaseOperations:
    """Optimized database operations with performance tracking."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.profiler = get_profiler()
    
    def optimized_batch_insert(self, 
                              table_name: str, 
                              data: List[Dict[str, Any]],
                              batch_size: int = 100) -> int:
        """Perform optimized batch insert with monitoring."""
        
        operation_name = f"db_batch_insert_{table_name}"
        with self.profiler.profile_operation(operation_name, len(data)) as metrics:
            
            total_inserted = 0
            
            # Process in smaller batches to prevent memory issues
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                try:
                    with self.db_manager.transaction() as conn:
                        # Dynamic query building based on first item's keys
                        if batch:
                            columns = list(batch[0].keys())
                            placeholders = ', '.join(['?' for _ in columns])
                            query = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                            
                            cursor = conn.cursor()
                            batch_values = [tuple(item[col] for col in columns) for item in batch]
                            cursor.executemany(query, batch_values)
                            
                            total_inserted += cursor.rowcount
                            
                except Exception as e:
                    metrics.errors_encountered += 1
                    logger.error(f"Batch insert error for {table_name}: {e}")
                    # Continue with next batch
                    continue
            
            logger.info(f"Batch insert completed: {total_inserted} rows inserted into {table_name}")
            return total_inserted


# Common Pattern: Memory Optimization
# ===================================

class MemoryOptimizer:
    """Memory optimization utilities and monitoring."""
    
    def __init__(self):
        self.profiler = get_profiler()
    
    @contextmanager
    def memory_efficient_processing(self, operation_name: str):
        """Context manager for memory-efficient processing."""
        import gc
        import psutil
        import os
        
        # Force garbage collection before starting
        gc.collect()
        
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with self.profiler.profile_operation(f"memory_{operation_name}") as metrics:
            try:
                yield metrics
            finally:
                # Clean up and measure final memory
                gc.collect()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_delta = end_memory - start_memory
                
                logger.debug(f"Memory delta for {operation_name}: {memory_delta:.1f}MB")
                
                # Alert if memory usage is high
                if memory_delta > 100:  # More than 100MB increase
                    logger.warning(f"High memory usage detected in {operation_name}: "
                                 f"{memory_delta:.1f}MB increase")
    
    def optimize_large_data_processing(self, 
                                     data_generator: Iterator[Any],
                                     processor_func: Callable[[Any], Any],
                                     batch_size: int = 50) -> Iterator[Any]:
        """Process large datasets with memory optimization."""
        
        with self.memory_efficient_processing("large_data_processing"):
            batch = []
            
            for item in data_generator:
                batch.append(item)
                
                if len(batch) >= batch_size:
                    # Process batch and yield results
                    for processed_item in self._process_batch(batch, processor_func):
                        yield processed_item
                    
                    # Clear batch from memory
                    batch.clear()
            
            # Process remaining items
            if batch:
                for processed_item in self._process_batch(batch, processor_func):
                    yield processed_item
    
    def _process_batch(self, batch: List[Any], processor_func: Callable[[Any], Any]) -> List[Any]:
        """Process a batch of items."""
        try:
            return [processor_func(item) for item in batch]
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return []


# Common Pattern: Resource Management
# ===================================

class ResourceManager:
    """Centralized resource management and monitoring."""
    
    def __init__(self):
        self.profiler = get_profiler()
        self._active_resources: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def managed_resource(self, resource_name: str, resource_factory: Callable[[], Any]):
        """Context manager for automatic resource management."""
        
        with self._lock:
            if resource_name in self._active_resources:
                resource = self._active_resources[resource_name]
            else:
                resource = resource_factory()
                self._active_resources[resource_name] = resource
        
        try:
            yield resource
        finally:
            # Resource cleanup is handled by the calling code or garbage collection
            pass
    
    def cleanup_resources(self):
        """Clean up all managed resources."""
        with self._lock:
            for name, resource in self._active_resources.items():
                try:
                    if hasattr(resource, 'close'):
                        resource.close()
                    elif hasattr(resource, 'cleanup'):
                        resource.cleanup()
                    logger.debug(f"Cleaned up resource: {name}")
                except Exception as e:
                    logger.warning(f"Error cleaning up resource {name}: {e}")
            
            self._active_resources.clear()


# Utility Functions for Common Operations
# ======================================

def time_function(func: Callable) -> Callable:
    """Decorator for timing function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = get_profiler()
        operation_name = f"function_{func.__name__}"
        
        with profiler.profile_operation(operation_name):
            return func(*args, **kwargs)
    
    return wrapper


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retrying operations with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    delay = base_delay * (2 ** attempt)
                    logger.debug(f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                               f"after {delay:.1f}s delay. Error: {e}")
                    time.sleep(delay)
        
        return wrapper
    return decorator


def chunked(iterable: List[Any], chunk_size: int) -> Iterator[List[Any]]:
    """Split an iterable into chunks of specified size."""
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]


def measure_operation_time(operation_name: str):
    """Context manager for measuring operation time."""
    return get_profiler().profile_operation(operation_name)


# Export main utilities
__all__ = [
    'PerformanceProfiler', 'BatchProcessor', 'CacheOperations', 
    'DatabaseOperations', 'MemoryOptimizer', 'ResourceManager',
    'get_profiler', 'time_function', 'retry_with_backoff', 
    'chunked', 'measure_operation_time'
]
