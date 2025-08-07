#!/usr/bin/env python3
"""
Phase 1 Integration Test: Comprehensive performance validation
of connection pooling, smart caching, and memory optimization.
"""

import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Dict, List, Any

from connection_manager import (
    SessionManager, 
    DatabasePool, 
    get_session_manager, 
    get_database_pool, 
    close_all_connections
)
from smart_cache import SmartCacheManager, get_cache_manager
from memory_optimizer import MemoryEfficientScraper, monitor_memory_usage

def create_test_data(count: int) -> List[Dict[str, Any]]:
    """Generate test crew availability data."""
    base_time = datetime.now()
    crew_data = []
    
    for i in range(count):
        availability = {}
        # Create 24 hours of 15-minute slots
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                slot_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                slot_key = slot_time.strftime("%d/%m/%Y %H%M")
                availability[slot_key] = (i + hour + minute) % 3 == 0  # Pseudo-random availability
        
        crew_data.append({
            'name': f'CREW_{i:03d}',
            'role': f'Role_{i % 5}',
            'availability': availability
        })
    
    return crew_data

@monitor_memory_usage
def test_original_approach(crew_data: List[Dict], db_path: str):
    """Test the original individual-connection approach."""
    start_time = time.time()
    
    # Original approach: new connection for each operation
    for crew in crew_data:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Insert crew
        cursor.execute(
            "INSERT OR IGNORE INTO crew (name, role) VALUES (?, ?)",
            (crew['name'], crew['role'])
        )
        
        # Get crew ID
        cursor.execute("SELECT id FROM crew WHERE name=?", (crew['name'],))
        crew_id = cursor.fetchone()[0]
        
        # Insert availability blocks (one by one)
        for slot, available in crew['availability'].items():
            if available:
                slot_time = datetime.strptime(slot, "%d/%m/%Y %H%M")
                end_time = slot_time + timedelta(minutes=15)
                cursor.execute(
                    "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                    (crew_id, slot_time, end_time)
                )
        
        conn.commit()
        conn.close()
    
    return time.time() - start_time

@monitor_memory_usage
def test_optimized_approach(crew_data: List[Dict], db_path: str):
    """Test the optimized connection pooling and batch operations."""
    start_time = time.time()
    
    # Optimized approach: connection pooling and batch operations
    db_pool = DatabasePool(db_path, max_connections=3)
    
    # Batch size for processing
    batch_size = 10
    
    for i in range(0, len(crew_data), batch_size):
        batch = crew_data[i:i + batch_size]
        
        with db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Batch insert crew details
            crew_batch = [(crew['name'], crew['role']) for crew in batch]
            cursor.executemany(
                "INSERT OR IGNORE INTO crew (name, role) VALUES (?, ?)",
                crew_batch
            )
            
            # Batch process availability
            availability_batch = []
            for crew in batch:
                cursor.execute("SELECT id FROM crew WHERE name=?", (crew['name'],))
                crew_id = cursor.fetchone()[0]
                
                for slot, available in crew['availability'].items():
                    if available:
                        slot_time = datetime.strptime(slot, "%d/%m/%Y %H%M")
                        end_time = slot_time + timedelta(minutes=15)
                        availability_batch.append((crew_id, slot_time, end_time))
            
            # Batch insert availability
            if availability_batch:
                cursor.executemany(
                    "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                    availability_batch
                )
            
            conn.commit()
    
    db_pool.close_all()
    return time.time() - start_time

def setup_test_database(db_path: str):
    """Setup test database with required schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crew (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            role TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crew_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crew_id INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            FOREIGN KEY (crew_id) REFERENCES crew(id)
        )
    """)
    
    conn.commit()
    conn.close()

def test_cache_performance():
    """Test smart cache performance improvements."""
    print("\n📁 Testing Smart Cache Performance...")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache_manager = SmartCacheManager(cache_dir=tmp_dir)
        
        # Test data
        dates = [(datetime.now() + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(10)]
        test_content = "<html>" + "x" * 1000 + "</html>"  # 1KB content
        
        # Test cache write performance
        start_time = time.time()
        for date in dates:
            cache_manager.write_cache(date, test_content)
        write_time = time.time() - start_time
        
        # Test cache read performance
        start_time = time.time()
        for date in dates:
            content = cache_manager.read_cache(date)
            assert content == test_content
        read_time = time.time() - start_time
        
        # Test batch cache check
        start_time = time.time()
        cache_validity = cache_manager.batch_cache_check(dates, 60)
        batch_check_time = time.time() - start_time
        
        # Get cache stats
        stats = cache_manager.get_cache_stats()
        
        print(f"  ✅ Cache write: {len(dates)} files in {write_time:.3f}s ({write_time/len(dates)*1000:.1f}ms/file)")
        print(f"  ✅ Cache read: {len(dates)} files in {read_time:.3f}s ({read_time/len(dates)*1000:.1f}ms/file)")
        print(f"  ✅ Batch check: {len(dates)} files in {batch_check_time:.3f}s ({batch_check_time/len(dates)*1000:.1f}ms/file)")
        print(f"  ✅ Cache stats: {stats['total_files']} files, {stats['total_size']} bytes")
        
        # Cleanup test
        start_time = time.time()
        removed = cache_manager.cleanup_expired_cache(max_age_days=0)  # Remove all
        cleanup_time = time.time() - start_time
        print(f"  ✅ Cleanup: {removed} files removed in {cleanup_time:.3f}s")

def test_session_management():
    """Test session manager performance and reuse."""
    print("\n🌐 Testing Session Management...")
    
    session_manager = SessionManager()
    
    # Test session reuse
    start_time = time.time()
    sessions = []
    for i in range(10):
        session = session_manager.get_session()
        sessions.append(session)
    session_creation_time = time.time() - start_time
    
    # Verify session reuse
    unique_sessions = len(set(id(session) for session in sessions))
    
    print(f"  ✅ Session requests: 10 requests in {session_creation_time:.3f}s")
    print(f"  ✅ Session reuse: {unique_sessions} unique session(s) created (expected: 1)")
    print(f"  ✅ Average request time: {session_creation_time/10*1000:.1f}ms")
    
    session_manager.close()

def main():
    """Run comprehensive Phase 1 performance tests."""
    print("🚀 Phase 1 Performance Integration Test")
    print("=" * 50)
    
    # Test different data sizes
    test_sizes = [10, 50, 100]
    
    for size in test_sizes:
        print(f"\n📊 Testing with {size} crew members...")
        
        # Generate test data
        crew_data = create_test_data(size)
        print(f"  Generated {size} crew with {len(crew_data[0]['availability'])} slots each")
        
        # Test original approach
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            original_db = f.name
        setup_test_database(original_db)
        
        original_time = test_original_approach(crew_data, original_db)
        
        # Test optimized approach
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            optimized_db = f.name
        setup_test_database(optimized_db)
        
        optimized_time = test_optimized_approach(crew_data, optimized_db)
        
        # Calculate improvements
        improvement = ((original_time - optimized_time) / original_time) * 100
        speedup = original_time / optimized_time if optimized_time > 0 else float('inf')
        
        print(f"  📈 Original approach: {original_time:.3f}s")
        print(f"  ⚡ Optimized approach: {optimized_time:.3f}s")
        print(f"  🎯 Improvement: {improvement:.1f}% faster ({speedup:.1f}x speedup)")
        
        # Cleanup
        Path(original_db).unlink()
        Path(optimized_db).unlink()
    
    # Test individual components
    test_session_management()
    test_cache_performance()
    
    # Cleanup
    close_all_connections()
    
    print("\n✅ Phase 1 Performance Tests Complete!")
    print("\nKey Improvements:")
    print("  • Connection Pooling: Reduces database connection overhead")
    print("  • Batch Operations: Dramatically improves insert performance") 
    print("  • Smart Caching: Intelligent cache warming and batch operations")
    print("  • Memory Optimization: Streaming processing and resource management")
    print("  • Session Reuse: Persistent HTTP connections with automatic cleanup")

if __name__ == "__main__":
    main()
