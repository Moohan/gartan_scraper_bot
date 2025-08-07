"""
Tests for Phase 3 Performance & Efficiency Improvements

This module tests the performance patterns, query optimization, and utility functions
implemented in Phase 3.
"""

import pytest
import tempfile
import sqlite3
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

# Import modules under test
from performance_patterns import (
    PerformanceProfiler, BatchProcessor, CacheOperations, 
    DatabaseOperations, MemoryOptimizer, ResourceManager,
    get_profiler, time_function, retry_with_backoff, chunked
)
from query_optimization import (
    QueryOptimizer, AdvancedCacheStrategy, BatchQueryProcessor,
    get_query_optimizer, get_cache_strategy, get_batch_processor,
    optimize_availability_query
)
from database_manager import DatabaseManager


class TestPerformanceProfiler:
    """Test the performance profiling functionality."""
    
    def test_profiler_initialization(self):
        """Test profiler initializes correctly."""
        profiler = PerformanceProfiler()
        assert profiler is not None
        assert len(profiler._metrics) == 0
        assert len(profiler._active_operations) == 0
    
    def test_profile_operation_context_manager(self):
        """Test profiling an operation with context manager."""
        profiler = PerformanceProfiler()
        
        with profiler.profile_operation("test_operation", 100) as metrics:
            time.sleep(0.1)  # Simulate work
            assert metrics.operation_name == "test_operation"
            assert metrics.items_processed == 100
        
        # Check metrics were recorded
        summary = profiler.get_performance_summary()
        assert "test_operation" in summary
        assert summary["test_operation"]["count"] == 1
        assert summary["test_operation"]["avg_duration"] >= 0.1
    
    def test_profiler_error_handling(self):
        """Test profiler handles errors correctly."""
        profiler = PerformanceProfiler()
        
        with pytest.raises(ValueError):
            with profiler.profile_operation("error_operation") as metrics:
                raise ValueError("Test error")
        
        # Check error was recorded
        summary = profiler.get_performance_summary()
        assert "error_operation" in summary
        assert summary["error_operation"]["total_errors"] == 1
    
    def test_performance_summary(self):
        """Test performance summary calculation."""
        profiler = PerformanceProfiler()
        
        # Run multiple operations
        for i in range(3):
            with profiler.profile_operation("repeated_operation", 10):
                time.sleep(0.05)
        
        summary = profiler.get_performance_summary()
        assert "repeated_operation" in summary
        assert summary["repeated_operation"]["count"] == 3
        assert summary["repeated_operation"]["avg_duration"] >= 0.05


class TestBatchProcessor:
    """Test the batch processing functionality."""
    
    def test_batch_processor_initialization(self):
        """Test batch processor initializes correctly."""
        processor = BatchProcessor(batch_size=25, max_workers=2)
        assert processor.batch_size == 25
        assert processor.max_workers == 2
    
    def test_process_in_batches(self):
        """Test batch processing with monitoring."""
        processor = BatchProcessor(batch_size=5)
        
        # Mock processor function
        def mock_processor(batch):
            return [item * 2 for item in batch]
        
        items = list(range(12))  # 12 items, should create 3 batches
        results = processor.process_in_batches(items, mock_processor, "test_batch")
        
        assert len(results) == 3  # 3 batches
        assert results[0] == [0, 2, 4, 6, 8]  # First batch processed
        assert results[1] == [10, 12, 14, 16, 18]  # Second batch processed
        assert results[2] == [20, 22]  # Third batch processed
    
    def test_batch_processor_error_handling(self):
        """Test batch processor handles errors in individual batches."""
        processor = BatchProcessor(batch_size=3)
        
        def error_processor(batch):
            if len(batch) == 3:  # First batch will error
                raise ValueError("Test error")
            return batch
        
        items = list(range(5))  # 5 items, 2 batches
        results = processor.process_in_batches(items, error_processor, "error_test")
        
        # Should only have result from second batch
        assert len(results) == 1
        assert results[0] == [3, 4]


class TestCacheOperations:
    """Test cache operations functionality."""
    
    def test_cache_operations_initialization(self):
        """Test cache operations initializes correctly."""
        mock_cache_manager = MagicMock()
        cache_ops = CacheOperations(mock_cache_manager)
        assert cache_ops.cache_manager == mock_cache_manager
    
    def test_batch_cache_check(self):
        """Test batch cache check operation."""
        mock_cache_manager = MagicMock()
        mock_cache_manager.batch_cache_check.return_value = {"date1": True, "date2": False}
        
        cache_ops = CacheOperations(mock_cache_manager)
        dates = ["date1", "date2"]
        
        result = cache_ops.batch_cache_operation(dates, "check")
        
        assert result == {"date1": True, "date2": False}
        mock_cache_manager.batch_cache_check.assert_called_once_with(dates, 15)
    
    def test_batch_cache_warm(self):
        """Test batch cache warm operation."""
        mock_cache_manager = MagicMock()
        mock_cache_manager.warm_cache_batch.return_value = {"date1": "content1"}
        
        cache_ops = CacheOperations(mock_cache_manager)
        dates = ["date1"]
        cache_minutes_map = {"date1": 30}
        
        result = cache_ops.batch_cache_operation(dates, "warm", cache_minutes_map)
        
        assert result == {"date1": "content1"}
        mock_cache_manager.warm_cache_batch.assert_called_once_with(None, dates, cache_minutes_map)
    
    def test_cache_cleanup(self):
        """Test cache cleanup operation."""
        mock_cache_manager = MagicMock()
        mock_cache_manager.cleanup_expired_cache.return_value = 5
        
        cache_ops = CacheOperations(mock_cache_manager)
        dates = []  # Not used for cleanup
        
        result = cache_ops.batch_cache_operation(dates, "cleanup")
        
        assert result == {"removed_files": 5}
        mock_cache_manager.cleanup_expired_cache.assert_called_once_with(max_age_days=30)


class TestDatabaseOperations:
    """Test database operations functionality."""
    
    def test_database_operations_initialization(self):
        """Test database operations initializes correctly."""
        mock_db_manager = MagicMock()
        db_ops = DatabaseOperations(mock_db_manager)
        assert db_ops.db_manager == mock_db_manager
    
    def test_optimized_batch_insert(self, tmp_path):
        """Test optimized batch insert functionality."""
        # Create test database
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(str(db_path))
        db_manager.ensure_schema()
        
        db_ops = DatabaseOperations(db_manager)
        
        # Test data
        test_data = [
            {"name": "John Doe", "role": "Firefighter"},
            {"name": "Jane Smith", "role": "Paramedic"},
            {"name": "Bob Johnson", "role": "Driver"}
        ]
        
        # Insert data
        inserted_count = db_ops.optimized_batch_insert("crew", test_data, batch_size=2)
        
        # Verify insertion
        assert inserted_count == 3
        
        # Check data was actually inserted
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM crew")
            count = cursor.fetchone()[0]
            assert count == 3


class TestMemoryOptimizer:
    """Test memory optimization functionality."""
    
    def test_memory_optimizer_initialization(self):
        """Test memory optimizer initializes correctly."""
        optimizer = MemoryOptimizer()
        assert optimizer is not None
    
    def test_memory_efficient_processing(self):
        """Test memory efficient processing context manager."""
        optimizer = MemoryOptimizer()
        
        with optimizer.memory_efficient_processing("test_memory") as metrics:
            # Simulate memory-intensive operation
            data = [i for i in range(1000)]
            assert len(data) == 1000
        
        # Should complete without errors
        assert metrics is not None
    
    def test_optimize_large_data_processing(self):
        """Test large data processing optimization."""
        optimizer = MemoryOptimizer()
        
        # Mock data generator
        def data_generator():
            for i in range(10):
                yield i
        
        def processor_func(item):
            return item * 2
        
        results = list(optimizer.optimize_large_data_processing(
            data_generator(), processor_func, batch_size=3
        ))
        
        assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]


class TestResourceManager:
    """Test resource management functionality."""
    
    def test_resource_manager_initialization(self):
        """Test resource manager initializes correctly."""
        manager = ResourceManager()
        assert manager is not None
        assert len(manager._active_resources) == 0
    
    def test_managed_resource(self):
        """Test managed resource context manager."""
        manager = ResourceManager()
        
        def create_resource():
            return {"id": 1, "data": "test"}
        
        with manager.managed_resource("test_resource", create_resource) as resource:
            assert resource == {"id": 1, "data": "test"}
        
        # Resource should be tracked
        assert "test_resource" in manager._active_resources
    
    def test_cleanup_resources(self):
        """Test resource cleanup functionality."""
        manager = ResourceManager()
        
        # Create mock resource with cleanup method
        mock_resource = MagicMock()
        manager._active_resources["test_resource"] = mock_resource
        
        manager.cleanup_resources()
        
        # Should attempt to close resource
        mock_resource.close.assert_called_once()
        assert len(manager._active_resources) == 0


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_time_function_decorator(self):
        """Test the timing function decorator."""
        @time_function
        def test_function():
            time.sleep(0.1)
            return "result"
        
        result = test_function()
        assert result == "result"
        
        # Check that profiling was performed
        profiler = get_profiler()
        summary = profiler.get_performance_summary()
        assert "function_test_function" in summary
    
    def test_retry_with_backoff_decorator(self):
        """Test the retry with backoff decorator."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 3
    
    def test_chunked_utility(self):
        """Test the chunked utility function."""
        items = list(range(10))
        chunks = list(chunked(items, 3))
        
        assert len(chunks) == 4
        assert chunks[0] == [0, 1, 2]
        assert chunks[1] == [3, 4, 5]
        assert chunks[2] == [6, 7, 8]
        assert chunks[3] == [9]


class TestQueryOptimizer:
    """Test query optimization functionality."""
    
    def test_query_optimizer_initialization(self, tmp_path):
        """Test query optimizer initializes correctly."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(str(db_path))
        db_manager.ensure_schema()
        
        optimizer = QueryOptimizer(db_manager)
        assert optimizer is not None
        assert len(optimizer._prepared_statements) > 0
        assert "crew_availability_range" in optimizer._prepared_statements
    
    def test_execute_optimized_query(self, tmp_path):
        """Test executing optimized queries."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(str(db_path))
        db_manager.ensure_schema()
        
        # Add test data
        with db_manager.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO crew (name, role) VALUES (?, ?)", ("John Doe", "Firefighter"))
        
        optimizer = QueryOptimizer(db_manager)
        
        # Test database stats query
        results = optimizer.execute_optimized_query("database_stats_optimized")
        
        assert len(results) > 0
        # Should have stats for all tables
        table_names = [result['table_name'] for result in results]
        assert 'crew' in table_names
        assert 'appliance' in table_names
    
    def test_query_caching(self, tmp_path):
        """Test query result caching."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(str(db_path))
        db_manager.ensure_schema()
        
        optimizer = QueryOptimizer(db_manager)
        
        # Execute query twice
        results1 = optimizer.execute_optimized_query("database_stats_optimized", use_cache=True)
        results2 = optimizer.execute_optimized_query("database_stats_optimized", use_cache=True)
        
        assert results1 == results2
        
        # Check cache was used (second call should be faster)
        stats = optimizer.get_query_performance_stats()
        assert "database_stats_optimized" in stats
    
    def test_optimize_database_indexes(self, tmp_path):
        """Test database index optimization."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(str(db_path))
        db_manager.ensure_schema()
        
        optimizer = QueryOptimizer(db_manager)
        
        # Should complete without errors
        optimizer.optimize_database_indexes()
        
        # Verify indexes were created (check one example)
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            assert len(indexes) > 0
            assert any('crew_availability' in idx for idx in indexes)


class TestAdvancedCacheStrategy:
    """Test advanced caching strategies."""
    
    def test_cache_strategy_initialization(self):
        """Test cache strategy initializes correctly."""
        cache = AdvancedCacheStrategy(max_cache_size=10)
        assert cache.max_cache_size == 10
        assert len(cache._cache_data) == 0
    
    def test_smart_cache_operations(self):
        """Test smart cache get/set operations."""
        cache = AdvancedCacheStrategy(max_cache_size=3)
        
        # Set some values
        cache.smart_cache_set("key1", "value1")
        cache.smart_cache_set("key2", "value2")
        
        # Get values
        assert cache.smart_cache_get("key1") == "value1"
        assert cache.smart_cache_get("key2") == "value2"
        assert cache.smart_cache_get("nonexistent") is None
    
    def test_cache_eviction(self):
        """Test cache eviction when full."""
        cache = AdvancedCacheStrategy(max_cache_size=2)
        
        # Fill cache
        cache.smart_cache_set("key1", "value1")
        cache.smart_cache_set("key2", "value2")
        
        # Add third item (should evict LRU)
        cache.smart_cache_set("key3", "value3")
        
        # key1 should be evicted
        assert cache.smart_cache_get("key1") is None
        assert cache.smart_cache_get("key2") == "value2"
        assert cache.smart_cache_get("key3") == "value3"
    
    def test_cache_expiry(self):
        """Test cache expiry functionality."""
        cache = AdvancedCacheStrategy()
        
        cache.smart_cache_set("key1", "value1")
        
        # Should be available immediately
        assert cache.smart_cache_get("key1", ttl=300) == "value1"
        
        # Should be expired with very short TTL
        assert cache.smart_cache_get("key1", ttl=0) is None


class TestBatchQueryProcessor:
    """Test batch query processing."""
    
    def test_batch_processor_initialization(self, tmp_path):
        """Test batch query processor initializes correctly."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(str(db_path))
        db_manager.ensure_schema()
        
        processor = BatchQueryProcessor(db_manager)
        assert processor is not None
    
    def test_batch_availability_lookup(self, tmp_path):
        """Test batch availability lookup."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(str(db_path))
        db_manager.ensure_schema()
        
        # Add test data
        with db_manager.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO crew (name, role) VALUES (?, ?)", ("John Doe", "Firefighter"))
            cursor.execute("INSERT INTO crew (name, role) VALUES (?, ?)", ("Jane Smith", "Paramedic"))
            
            # Add availability data
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=1)
            cursor.execute("""
                INSERT INTO crew_availability (crew_id, start_time, end_time) 
                VALUES (1, ?, ?)
            """, (start_time, end_time))
        
        processor = BatchQueryProcessor(db_manager)
        
        # Test batch lookup
        results = processor.batch_availability_lookup(
            [1, 2], "crew", start_time - timedelta(hours=1), end_time + timedelta(hours=1)
        )
        
        assert 1 in results
        assert len(results[1]) == 1
        assert 2 not in results or len(results[2]) == 0
    
    def test_batch_entity_lookup(self, tmp_path):
        """Test batch entity lookup by names."""
        db_path = tmp_path / "test.db"
        db_manager = DatabaseManager(str(db_path))
        db_manager.ensure_schema()
        
        # Add test data
        with db_manager.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO crew (name, role) VALUES (?, ?)", ("John Doe", "Firefighter"))
            cursor.execute("INSERT INTO crew (name, role) VALUES (?, ?)", ("Jane Smith", "Paramedic"))
        
        processor = BatchQueryProcessor(db_manager)
        
        # Test batch lookup
        results = processor.batch_entity_lookup(["John Doe", "Jane Smith", "Nonexistent"], "crew")
        
        assert "John Doe" in results
        assert "Jane Smith" in results
        assert "Nonexistent" not in results
        assert results["John Doe"] == 1
        assert results["Jane Smith"] == 2


class TestOptimizationUtilities:
    """Test optimization utility functions."""
    
    def test_optimize_availability_query(self):
        """Test availability query optimization."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)
        
        query_plan = optimize_availability_query(
            start_date, end_date, "crew", ["John Doe", "Jane Smith"]
        )
        
        assert query_plan is not None
        assert "crew" in query_plan.query
        assert "crew_availability" in query_plan.query
        assert len(query_plan.parameters) == 4  # start_date, end_date, 2 names
        assert query_plan.estimated_rows == 2
        assert len(query_plan.index_usage) > 0


if __name__ == "__main__":
    pytest.main([__file__])
