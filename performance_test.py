#!/usr/bin/env python3
"""
Performance comparison test for Phase 1 optimizations.
"""

import time
import sqlite3
import tempfile
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Original implementation (simplified)
def original_db_insert(data: List[Dict], db_path: str):
    """Original single-insert approach."""
    for item in data:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO test_table (name, value, timestamp) VALUES (?, ?, ?)",
            (item['name'], item['value'], item['timestamp'])
        )
        conn.commit()
        conn.close()

# Optimized implementation
def optimized_db_insert(data: List[Dict], db_path: str):
    """Optimized batch-insert approach."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Batch insert
    batch_data = [
        (item['name'], item['value'], item['timestamp']) 
        for item in data
    ]
    cursor.executemany(
        "INSERT INTO test_table (name, value, timestamp) VALUES (?, ?, ?)",
        batch_data
    )
    conn.commit()
    conn.close()

def setup_test_db(db_path: str):
    """Setup test database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value INTEGER,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def generate_test_data(count: int) -> List[Dict]:
    """Generate test data."""
    now = datetime.now()
    return [
        {
            'name': f'crew_{i}',
            'value': i,
            'timestamp': (now + timedelta(minutes=i)).isoformat()
        }
        for i in range(count)
    ]

def benchmark_performance():
    """Benchmark the performance improvements."""
    test_sizes = [10, 50, 100, 200]
    
    print("Performance Benchmark: Database Optimization")
    print("=" * 50)
    
    for size in test_sizes:
        print(f"\nTesting with {size} records:")
        
        # Generate test data
        test_data = generate_test_data(size)
        
        # Test original approach
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            original_db = f.name
        setup_test_db(original_db)
        
        start_time = time.time()
        original_db_insert(test_data, original_db)
        original_time = time.time() - start_time
        
        # Test optimized approach  
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            optimized_db = f.name
        setup_test_db(optimized_db)
        
        start_time = time.time()
        optimized_db_insert(test_data, optimized_db)
        optimized_time = time.time() - start_time
        
        # Calculate improvement
        improvement = ((original_time - optimized_time) / original_time) * 100
        speedup = original_time / optimized_time if optimized_time > 0 else float('inf')
        
        print(f"  Original:   {original_time:.4f}s")
        print(f"  Optimized:  {optimized_time:.4f}s")
        print(f"  Improvement: {improvement:.1f}% faster ({speedup:.1f}x speedup)")
        
        # Cleanup
        os.unlink(original_db)
        os.unlink(optimized_db)

if __name__ == "__main__":
    benchmark_performance()
