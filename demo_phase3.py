"""
Phase 3 Performance & Efficiency Improvements Demo

This demo showcases the performance optimizations, common pattern extraction,
and advanced query optimization implemented in Phase 3.
"""

import time
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import Phase 3 modules
from performance_patterns import (
    get_profiler, BatchProcessor, MemoryOptimizer, 
    time_function, retry_with_backoff
)
from query_optimization import (
    get_query_optimizer, get_cache_strategy, get_batch_processor
)
from database_manager import DatabaseManager


def create_sample_data(count: int = 100) -> List[Dict[str, Any]]:
    """Create sample data for performance testing."""
    base_time = datetime.now()
    
    return [
        {
            'name': f'Crew Member {i}',
            'role': 'Firefighter' if i % 2 == 0 else 'Paramedic',
            'availability': {
                f"{(base_time + timedelta(hours=h)).strftime('%d/%m/%Y %H%M')}": h % 3 == 0
                for h in range(0, 24, 1)  # 24 hours of availability data
            }
        }
        for i in range(count)
    ]


@time_function
def traditional_processing(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """Traditional processing approach (for comparison)."""
    processed = 0
    availability_count = 0
    
    for item in data:
        processed += 1
        for slot, available in item['availability'].items():
            if available:
                availability_count += 1
        time.sleep(0.001)  # Simulate processing overhead
    
    return {'processed': processed, 'availability_slots': availability_count}


def optimized_processing_demo():
    """Demonstrate optimized processing patterns from Phase 3."""
    print("🚀 Phase 3 Performance & Efficiency Demo")
    print("=" * 50)
    
    # Create sample data
    print("\n📊 Creating sample data...")
    sample_data = create_sample_data(50)
    print(f"Created {len(sample_data)} crew members with availability data")
    
    # Demo 1: Performance Profiling
    print("\n1️⃣ Performance Profiling Demo")
    print("-" * 30)
    
    profiler = get_profiler()
    
    # Traditional approach
    print("Traditional processing:")
    result1 = traditional_processing(sample_data)
    print(f"  Result: {result1}")
    
    # Optimized approach with profiling
    print("Optimized processing with profiling:")
    
    @time_function
    def optimized_processing(data: List[Dict[str, Any]]) -> Dict[str, int]:
        processed = 0
        availability_count = 0
        
        # Use batch processing for efficiency
        processor = BatchProcessor(batch_size=10)
        
        def process_batch(batch):
            batch_processed = len(batch)
            batch_availability = sum(
                sum(1 for available in item['availability'].values() if available)
                for item in batch
            )
            return {'processed': batch_processed, 'availability': batch_availability}
        
        results = processor.process_in_batches(data, process_batch, "crew_processing")
        
        for result in results:
            processed += result['processed']
            availability_count += result['availability']
        
        return {'processed': processed, 'availability_slots': availability_count}
    
    result2 = optimized_processing(sample_data)
    print(f"  Result: {result2}")
    
    # Show performance summary
    summary = profiler.get_performance_summary()
    print("\n📈 Performance Summary:")
    for operation, stats in summary.items():
        print(f"  {operation}:")
        print(f"    Count: {stats['count']}")
        print(f"    Avg Duration: {stats['avg_duration']:.4f}s")
        print(f"    Min/Max: {stats['min_duration']:.4f}s / {stats['max_duration']:.4f}s")
    
    # Demo 2: Memory Optimization
    print("\n2️⃣ Memory Optimization Demo")
    print("-" * 30)
    
    memory_optimizer = MemoryOptimizer()
    
    # Memory-efficient large data processing
    def data_generator():
        for i in range(200):  # Larger dataset
            yield {
                'id': i,
                'data': [j for j in range(100)]  # Some memory-intensive data
            }
    
    def processor_func(item):
        return {'id': item['id'], 'sum': sum(item['data'])}
    
    print("Processing large dataset with memory optimization...")
    
    with memory_optimizer.memory_efficient_processing("large_dataset") as metrics:
        results = list(memory_optimizer.optimize_large_data_processing(
            data_generator(), processor_func, batch_size=20
        ))
        
        print(f"  Processed {len(results)} items")
        print(f"  Sample results: {results[:3]}...")
    
    # Demo 3: Database Query Optimization
    print("\n3️⃣ Database Query Optimization Demo")
    print("-" * 30)
    
    # Create temporary database for demo
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db_manager = DatabaseManager(db_path)
    db_manager.ensure_schema()
    
    # Set up query optimizer
    query_optimizer = get_query_optimizer()
    query_optimizer.db_manager = db_manager
    
    # Create optimized indexes
    print("Creating optimized database indexes...")
    query_optimizer.optimize_database_indexes()
    
    # Add sample data to database
    print("Adding sample data to database...")
    with db_manager.transaction() as conn:
        cursor = conn.cursor()
        
        # Add crew data
        for i, crew in enumerate(sample_data[:20]):  # Use subset for demo
            cursor.execute("INSERT INTO crew (name, role) VALUES (?, ?)", 
                         (crew['name'], crew['role']))
            
            # Add availability data
            crew_id = i + 1
            for slot, available in crew['availability'].items():
                if available:
                    try:
                        start_time = datetime.strptime(slot, '%d/%m/%Y %H%M')
                        end_time = start_time + timedelta(minutes=15)
                        cursor.execute("""
                            INSERT INTO crew_availability (crew_id, start_time, end_time)
                            VALUES (?, ?, ?)
                        """, (crew_id, start_time, end_time))
                    except ValueError:
                        continue  # Skip invalid time formats
    
    # Test optimized queries
    print("Testing optimized queries...")
    
    # Database stats query
    stats_results = query_optimizer.execute_optimized_query('database_stats_optimized')
    print("  Database statistics:")
    for stat in stats_results:
        print(f"    {stat['table_name']}: {stat['row_count']} rows")
    
    # Crew availability range query
    start_date = datetime.now()
    end_date = start_date + timedelta(days=1)
    
    availability_results = query_optimizer.execute_optimized_query(
        'crew_availability_range', 
        (start_date, end_date)
    )
    print(f"  Availability query returned {len(availability_results)} results")
    
    # Show query performance stats
    query_stats = query_optimizer.get_query_performance_stats()
    print("\n📊 Query Performance Statistics:")
    for query_name, stats in query_stats.items():
        print(f"  {query_name}:")
        print(f"    Executions: {stats['count']}")
        print(f"    Avg Time: {stats['avg_time']:.4f}s")
        print(f"    Total Time: {stats['total_time']:.4f}s")
    
    # Demo 4: Advanced Caching
    print("\n4️⃣ Advanced Caching Demo")
    print("-" * 30)
    
    cache_strategy = get_cache_strategy()
    
    # Simulate caching operations
    print("Testing smart cache operations...")
    
    # Cache some data
    for i in range(10):
        cache_strategy.smart_cache_set(f"key_{i}", f"value_{i}")
    
    # Test cache hits and misses
    hits = 0
    misses = 0
    
    for i in range(15):  # Test beyond cache size
        result = cache_strategy.smart_cache_get(f"key_{i}")
        if result:
            hits += 1
        else:
            misses += 1
    
    print(f"  Cache hits: {hits}")
    print(f"  Cache misses: {misses}")
    
    # Show cache statistics
    cache_stats = cache_strategy.get_cache_stats()
    print(f"  Cache utilization: {cache_stats['utilization']:.2%}")
    print(f"  Total access count: {cache_stats['total_access_count']}")
    
    # Demo 5: Batch Query Processing
    print("\n5️⃣ Batch Query Processing Demo")
    print("-" * 30)
    
    batch_processor = get_batch_processor()
    batch_processor.db_manager = db_manager
    
    # Test batch entity lookup
    crew_names = [f'Crew Member {i}' for i in range(5)]
    name_to_id_map = batch_processor.batch_entity_lookup(crew_names, 'crew')
    
    print(f"  Batch entity lookup: {len(name_to_id_map)} entities found")
    print(f"  Sample mapping: {dict(list(name_to_id_map.items())[:3])}")
    
    # Test batch availability lookup
    entity_ids = list(name_to_id_map.values())
    availability_map = batch_processor.batch_availability_lookup(
        entity_ids, 'crew', start_date, end_date
    )
    
    availability_count = sum(len(slots) for slots in availability_map.values())
    print(f"  Batch availability lookup: {availability_count} availability slots found")
    
    # Demo 6: Retry with Backoff
    print("\n6️⃣ Retry with Backoff Demo")
    print("-" * 30)
    
    attempt_count = 0
    
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    def unreliable_operation():
        nonlocal attempt_count
        attempt_count += 1
        print(f"    Attempt {attempt_count}")
        
        if attempt_count < 3:
            raise ConnectionError("Simulated network error")
        return "Success!"
    
    print("Testing retry mechanism with backoff:")
    try:
        result = unreliable_operation()
        print(f"  Final result: {result}")
    except Exception as e:
        print(f"  Failed after retries: {e}")
    
    # Final Performance Summary
    print("\n🎯 Final Performance Summary")
    print("=" * 50)
    
    final_summary = profiler.get_performance_summary()
    total_operations = sum(stats['count'] for stats in final_summary.values())
    total_time = sum(stats['avg_duration'] * stats['count'] for stats in final_summary.values())
    
    print(f"Total operations profiled: {total_operations}")
    print(f"Total execution time: {total_time:.4f}s")
    print(f"Average operation time: {total_time/total_operations:.4f}s")
    
    print("\nTop 5 operations by total time:")
    sorted_ops = sorted(final_summary.items(), 
                       key=lambda x: x[1]['avg_duration'] * x[1]['count'], 
                       reverse=True)
    
    for i, (op_name, stats) in enumerate(sorted_ops[:5], 1):
        total_op_time = stats['avg_duration'] * stats['count']
        print(f"  {i}. {op_name}: {total_op_time:.4f}s ({stats['count']} executions)")
    
    # Cleanup
    import os
    try:
        os.unlink(db_path)
    except:
        pass
    
    print("\n✅ Phase 3 Demo Complete!")
    print("Key improvements demonstrated:")
    print("  • Performance profiling and monitoring")
    print("  • Memory-efficient processing for large datasets")
    print("  • Optimized database queries with indexing")
    print("  • Advanced caching strategies with smart eviction")
    print("  • Batch processing for improved throughput")
    print("  • Retry mechanisms with exponential backoff")


if __name__ == "__main__":
    optimized_processing_demo()
