"""
Database Query Optimization Module

This module provides optimized database queries and advanced caching strategies
for improved performance in Phase 3 improvements.
"""

import sqlite3
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from logging_config import get_logger
from database_manager import get_database_manager
from performance_patterns import get_profiler, time_function

logger = get_logger()

@dataclass
class QueryPlan:
    """Container for query execution plan and optimization information."""
    query: str
    parameters: Tuple[Any, ...]
    estimated_rows: int
    index_usage: List[str]
    execution_time_estimate: float
    cache_key: Optional[str] = None


class QueryOptimizer:
    """Advanced query optimization and caching for database operations."""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_database_manager()
        self.profiler = get_profiler()
        self._query_cache: Dict[str, Any] = {}
        self._query_stats: Dict[str, List[float]] = {}
        self._prepared_statements: Dict[str, str] = {}
        
        # Initialize optimized queries
        self._init_optimized_queries()
    
    def _init_optimized_queries(self):
        """Initialize commonly used optimized queries."""
        self._prepared_statements.update({
            'crew_availability_range': """
                SELECT ca.crew_id, c.name, ca.start_time, ca.end_time
                FROM crew_availability ca
                JOIN crew c ON ca.crew_id = c.id
                WHERE ca.start_time >= ? AND ca.end_time <= ?
                ORDER BY c.name, ca.start_time
            """,
            
            'appliance_availability_range': """
                SELECT aa.appliance_id, a.name, aa.start_time, aa.end_time
                FROM appliance_availability aa
                JOIN appliance a ON aa.appliance_id = a.id
                WHERE aa.start_time >= ? AND aa.end_time <= ?
                ORDER BY a.name, aa.start_time
            """,
            
            'crew_next_available': """
                SELECT c.id, c.name, 
                       MIN(ca.start_time) as next_available_time
                FROM crew c
                LEFT JOIN crew_availability ca ON c.id = ca.crew_id 
                    AND ca.start_time > ?
                GROUP BY c.id, c.name
                ORDER BY c.name
            """,
            
            'availability_overlap_check': """
                SELECT COUNT(*) as overlap_count
                FROM crew_availability
                WHERE crew_id = ? 
                  AND start_time < ? 
                  AND end_time > ?
            """,
            
            'database_stats_optimized': """
                SELECT 
                    'crew' as table_name, COUNT(*) as row_count FROM crew
                UNION ALL
                SELECT 
                    'appliance' as table_name, COUNT(*) as row_count FROM appliance
                UNION ALL
                SELECT 
                    'crew_availability' as table_name, COUNT(*) as row_count FROM crew_availability
                UNION ALL
                SELECT 
                    'appliance_availability' as table_name, COUNT(*) as row_count FROM appliance_availability
            """,
            
            'crew_utilization_stats': """
                SELECT 
                    c.name,
                    COUNT(ca.id) as availability_blocks,
                    SUM((julianday(ca.end_time) - julianday(ca.start_time)) * 24 * 60) as total_minutes,
                    MIN(ca.start_time) as earliest_available,
                    MAX(ca.end_time) as latest_available
                FROM crew c
                LEFT JOIN crew_availability ca ON c.id = ca.crew_id
                WHERE ca.start_time >= ? AND ca.end_time <= ?
                GROUP BY c.id, c.name
                ORDER BY total_minutes DESC
            """,
            
            'appliance_utilization_stats': """
                SELECT 
                    a.name,
                    COUNT(aa.id) as availability_blocks,
                    SUM((julianday(aa.end_time) - julianday(aa.start_time)) * 24 * 60) as total_minutes,
                    MIN(aa.start_time) as earliest_available,
                    MAX(aa.end_time) as latest_available
                FROM appliance a
                LEFT JOIN appliance_availability aa ON a.id = aa.appliance_id
                WHERE aa.start_time >= ? AND aa.end_time <= ?
                GROUP BY a.id, a.name
                ORDER BY total_minutes DESC
            """
        })
    
    @time_function
    def execute_optimized_query(self, 
                               query_name: str, 
                               parameters: Tuple[Any, ...] = (),
                               use_cache: bool = True,
                               cache_ttl: int = 300) -> List[Dict[str, Any]]:
        """Execute an optimized query with caching."""
        
        if query_name not in self._prepared_statements:
            raise ValueError(f"Unknown optimized query: {query_name}")
        
        query = self._prepared_statements[query_name]
        cache_key = f"{query_name}:{hash(parameters)}" if use_cache else None
        
        # Check cache first
        if cache_key and cache_key in self._query_cache:
            cached_result, cached_time = self._query_cache[cache_key]
            if time.time() - cached_time < cache_ttl:
                logger.debug(f"Query cache hit for {query_name}")
                return cached_result
        
        # Execute query with performance monitoring
        operation_name = f"query_{query_name}"
        with self.profiler.profile_operation(operation_name) as metrics:
            start_time = time.time()
            
            with self.db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, parameters)
                
                results = [dict(row) for row in cursor.fetchall()]
                
            execution_time = time.time() - start_time
            
            # Track query performance
            if query_name not in self._query_stats:
                self._query_stats[query_name] = []
            self._query_stats[query_name].append(execution_time)
            
            # Cache result if requested
            if cache_key:
                self._query_cache[cache_key] = (results, time.time())
            
            metrics.items_processed = len(results)
            logger.debug(f"Query {query_name} executed: {len(results)} rows in {execution_time:.3f}s")
            
            return results
    
    def get_query_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for all executed queries."""
        stats = {}
        
        for query_name, execution_times in self._query_stats.items():
            if execution_times:
                stats[query_name] = {
                    'count': len(execution_times),
                    'avg_time': sum(execution_times) / len(execution_times),
                    'min_time': min(execution_times),
                    'max_time': max(execution_times),
                    'total_time': sum(execution_times)
                }
        
        return stats
    
    def clear_query_cache(self):
        """Clear the query cache."""
        self._query_cache.clear()
        logger.debug("Query cache cleared")
    
    def optimize_database_indexes(self):
        """Create optimized indexes for better query performance."""
        
        indexes_to_create = [
            # Crew availability indexes
            "CREATE INDEX IF NOT EXISTS idx_crew_availability_crew_id ON crew_availability(crew_id)",
            "CREATE INDEX IF NOT EXISTS idx_crew_availability_time_range ON crew_availability(start_time, end_time)",
            "CREATE INDEX IF NOT EXISTS idx_crew_availability_start_time ON crew_availability(start_time)",
            
            # Appliance availability indexes
            "CREATE INDEX IF NOT EXISTS idx_appliance_availability_appliance_id ON appliance_availability(appliance_id)",
            "CREATE INDEX IF NOT EXISTS idx_appliance_availability_time_range ON appliance_availability(start_time, end_time)",
            "CREATE INDEX IF NOT EXISTS idx_appliance_availability_start_time ON appliance_availability(start_time)",
            
            # Entity name indexes for faster lookups
            "CREATE INDEX IF NOT EXISTS idx_crew_name ON crew(name)",
            "CREATE INDEX IF NOT EXISTS idx_appliance_name ON appliance(name)",
            
            # Compound indexes for common query patterns
            "CREATE INDEX IF NOT EXISTS idx_crew_availability_composite ON crew_availability(crew_id, start_time, end_time)",
            "CREATE INDEX IF NOT EXISTS idx_appliance_availability_composite ON appliance_availability(appliance_id, start_time, end_time)"
        ]
        
        with self.profiler.profile_operation("create_database_indexes") as metrics:
            with self.db_manager.transaction() as conn:
                cursor = conn.cursor()
                
                for index_sql in indexes_to_create:
                    try:
                        cursor.execute(index_sql)
                        logger.debug(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                    except sqlite3.Error as e:
                        logger.warning(f"Failed to create index: {e}")
                
                metrics.items_processed = len(indexes_to_create)
        
        logger.info(f"Database indexes optimized: {len(indexes_to_create)} indexes processed")


class AdvancedCacheStrategy:
    """Advanced caching strategies for different data patterns."""
    
    def __init__(self, max_cache_size: int = 1000):
        self.max_cache_size = max_cache_size
        self._cache_data: Dict[str, Tuple[Any, float, int]] = {}  # data, timestamp, access_count
        self._cache_access_order: List[str] = []
        self.profiler = get_profiler()
    
    def smart_cache_get(self, key: str, ttl: int = 300) -> Optional[Any]:
        """Get item from cache with smart eviction."""
        
        if key not in self._cache_data:
            return None
        
        data, timestamp, access_count = self._cache_data[key]
        
        # Check if expired
        if time.time() - timestamp > ttl:
            self._evict_key(key)
            return None
        
        # Update access count and order
        self._cache_data[key] = (data, timestamp, access_count + 1)
        self._update_access_order(key)
        
        return data
    
    def smart_cache_set(self, key: str, value: Any) -> None:
        """Set item in cache with smart eviction."""
        
        # Evict if cache is full
        if len(self._cache_data) >= self.max_cache_size and key not in self._cache_data:
            self._evict_lru()
        
        self._cache_data[key] = (value, time.time(), 1)
        self._update_access_order(key)
    
    def _evict_key(self, key: str) -> None:
        """Evict a specific key from cache."""
        if key in self._cache_data:
            del self._cache_data[key]
        if key in self._cache_access_order:
            self._cache_access_order.remove(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if self._cache_access_order:
            lru_key = self._cache_access_order[0]
            self._evict_key(lru_key)
    
    def _update_access_order(self, key: str) -> None:
        """Update the access order for LRU tracking."""
        if key in self._cache_access_order:
            self._cache_access_order.remove(key)
        self._cache_access_order.append(key)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'size': len(self._cache_data),
            'max_size': self.max_cache_size,
            'utilization': len(self._cache_data) / self.max_cache_size,
            'total_access_count': sum(access_count for _, _, access_count in self._cache_data.values())
        }


class BatchQueryProcessor:
    """Optimized batch processing for database queries."""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_database_manager()
        self.profiler = get_profiler()
    
    @time_function
    def batch_availability_lookup(self, 
                                 entity_ids: List[int], 
                                 entity_type: str,
                                 start_date: datetime,
                                 end_date: datetime) -> Dict[int, List[Dict[str, Any]]]:
        """Batch lookup of availability for multiple entities."""
        
        if entity_type not in ['crew', 'appliance']:
            raise ValueError(f"Invalid entity type: {entity_type}")
        
        table_name = f"{entity_type}_availability"
        entity_id_column = f"{entity_type}_id"
        
        # Build optimized batch query
        placeholders = ', '.join(['?' for _ in entity_ids])
        query = f"""
            SELECT {entity_id_column}, start_time, end_time
            FROM {table_name}
            WHERE {entity_id_column} IN ({placeholders})
              AND start_time >= ?
              AND end_time <= ?
            ORDER BY {entity_id_column}, start_time
        """
        
        parameters = tuple(entity_ids) + (start_date, end_date)
        
        operation_name = f"batch_availability_lookup_{entity_type}"
        with self.profiler.profile_operation(operation_name, len(entity_ids)) as metrics:
            
            with self.db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, parameters)
                
                # Group results by entity_id
                results = {}
                for row in cursor.fetchall():
                    entity_id = row[entity_id_column]
                    if entity_id not in results:
                        results[entity_id] = []
                    
                    results[entity_id].append({
                        'start_time': row['start_time'],
                        'end_time': row['end_time']
                    })
                
                metrics.items_processed = len(results)
                return results
    
    @time_function
    def batch_entity_lookup(self, names: List[str], entity_type: str) -> Dict[str, int]:
        """Batch lookup of entity IDs by names."""
        
        if entity_type not in ['crew', 'appliance']:
            raise ValueError(f"Invalid entity type: {entity_type}")
        
        placeholders = ', '.join(['?' for _ in names])
        query = f"""
            SELECT id, name
            FROM {entity_type}
            WHERE name IN ({placeholders})
        """
        
        operation_name = f"batch_entity_lookup_{entity_type}"
        with self.profiler.profile_operation(operation_name, len(names)) as metrics:
            
            with self.db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, names)
                
                results = {row['name']: row['id'] for row in cursor.fetchall()}
                metrics.items_processed = len(results)
                return results


# Global instances
_query_optimizer = None
_cache_strategy = None
_batch_processor = None

def get_query_optimizer() -> QueryOptimizer:
    """Get the global query optimizer instance."""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer

def get_cache_strategy() -> AdvancedCacheStrategy:
    """Get the global cache strategy instance."""
    global _cache_strategy
    if _cache_strategy is None:
        _cache_strategy = AdvancedCacheStrategy()
    return _cache_strategy

def get_batch_processor() -> BatchQueryProcessor:
    """Get the global batch query processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchQueryProcessor()
    return _batch_processor


# Utility functions for common optimizations
@lru_cache(maxsize=128)
def cached_entity_count(entity_type: str) -> int:
    """Get cached entity count with LRU caching."""
    optimizer = get_query_optimizer()
    results = optimizer.execute_optimized_query('database_stats_optimized')
    
    for result in results:
        if result['table_name'] == entity_type:
            return result['row_count']
    
    return 0


def optimize_availability_query(start_date: datetime, 
                               end_date: datetime, 
                               entity_type: str,
                               entity_names: Optional[List[str]] = None) -> QueryPlan:
    """Create an optimized query plan for availability lookup."""
    
    if entity_type not in ['crew', 'appliance']:
        raise ValueError(f"Invalid entity type: {entity_type}")
    
    # Build optimized query based on parameters
    base_query = f"""
        SELECT e.id, e.name, a.start_time, a.end_time
        FROM {entity_type} e
        LEFT JOIN {entity_type}_availability a ON e.id = a.{entity_type}_id
        WHERE a.start_time >= ? AND a.end_time <= ?
    """
    
    parameters = [start_date, end_date]
    
    if entity_names:
        placeholders = ', '.join(['?' for _ in entity_names])
        base_query += f" AND e.name IN ({placeholders})"
        parameters.extend(entity_names)
    
    base_query += f" ORDER BY e.name, a.start_time"
    
    # Estimate performance characteristics
    estimated_rows = len(entity_names) if entity_names else cached_entity_count(entity_type)
    
    return QueryPlan(
        query=base_query,
        parameters=tuple(parameters),
        estimated_rows=estimated_rows,
        index_usage=[f"idx_{entity_type}_availability_time_range", f"idx_{entity_type}_name"],
        execution_time_estimate=estimated_rows * 0.001,  # Rough estimate
        cache_key=f"availability_{entity_type}_{hash(tuple(parameters))}"
    )


# Export main components
__all__ = [
    'QueryOptimizer', 'AdvancedCacheStrategy', 'BatchQueryProcessor',
    'QueryPlan', 'get_query_optimizer', 'get_cache_strategy', 
    'get_batch_processor', 'optimize_availability_query'
]
