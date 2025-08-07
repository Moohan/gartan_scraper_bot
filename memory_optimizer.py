"""
Memory-optimized scraper implementation with batch processing and resource management.

Implements streaming data processing, memory-efficient parsing, and intelligent
resource allocation for improved performance with large datasets.
"""

import gc
import sys
from typing import Iterator, List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import concurrent.futures
import threading
from dataclasses import dataclass
from logging_config import get_logger
from connection_manager import get_database_pool
from smart_cache import get_cache_manager

logger = get_logger()

@dataclass
class ProcessingBatch:
    """Container for a batch of processing data."""
    dates: List[str]
    crew_data: List[Dict[str, Any]]
    appliance_data: Dict[str, Any]
    processing_time: float
    memory_usage: Optional[int] = None

class MemoryEfficientScraper:
    """Memory-optimized scraper with streaming processing and resource management."""
    
    def __init__(self, 
                 batch_size: int = 5,
                 max_workers: int = 3,
                 memory_limit_mb: int = 500):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.cache_manager = get_cache_manager()
        
        # Processing statistics
        self.stats = {
            'total_dates': 0,
            'processed_dates': 0,
            'failed_dates': 0,
            'cache_hits': 0,
            'memory_cleanups': 0,
            'batch_count': 0
        }
    
    def get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss
        except ImportError:
            # Fallback to basic memory tracking
            return sys.getsizeof(gc.get_objects())
    
    def should_force_gc(self) -> bool:
        """Check if we should force garbage collection."""
        memory_usage = self.get_memory_usage()
        return memory_usage > self.memory_limit_bytes
    
    def cleanup_memory(self):
        """Force memory cleanup and garbage collection."""
        gc.collect()
        self.stats['memory_cleanups'] += 1
        logger.debug(f"Memory cleanup performed (#{self.stats['memory_cleanups']})")
    
    def generate_date_batches(self, start_date: datetime, max_days: int) -> Iterator[List[str]]:
        """Generate batches of dates for processing."""
        dates = []
        for day_offset in range(max_days):
            booking_date = (start_date + timedelta(days=day_offset)).strftime("%d/%m/%Y")
            dates.append(booking_date)
            
            # Yield batch when full
            if len(dates) >= self.batch_size:
                yield dates
                dates = []
        
        # Yield remaining dates
        if dates:
            yield dates
    
    def process_date_batch(self, session, dates: List[str], cache_minutes_map: Dict[str, int]) -> ProcessingBatch:
        """Process a batch of dates efficiently."""
        start_time = time.time()
        
        # Use smart cache for batch warming
        cache_results = self.cache_manager.warm_cache_batch(session, dates, cache_minutes_map)
        
        crew_data_batch = []
        appliance_data_batch = {}
        
        # Process each date in the batch
        for date in dates:
            try:
                html_content = cache_results.get(date)
                if not html_content:
                    logger.warning(f"No HTML content for {date}")
                    self.stats['failed_dates'] += 1
                    continue
                
                # Memory-efficient parsing (process and discard immediately)
                crew_list, appliance_dict = self._parse_html_streaming(html_content, date)
                
                # Accumulate results
                crew_data_batch.extend(crew_list)
                
                # Merge appliance data efficiently
                for appliance, data in appliance_dict.items():
                    if appliance not in appliance_data_batch:
                        appliance_data_batch[appliance] = data
                    else:
                        # Merge availability data
                        appliance_data_batch[appliance]['availability'].update(data['availability'])
                
                self.stats['processed_dates'] += 1
                
                # Clear HTML content from memory immediately
                del html_content
                
            except Exception as e:
                logger.error(f"Error processing {date}: {e}")
                self.stats['failed_dates'] += 1
        
        processing_time = time.time() - start_time
        memory_usage = self.get_memory_usage()
        
        return ProcessingBatch(
            dates=dates,
            crew_data=crew_data_batch,
            appliance_data=appliance_data_batch,
            processing_time=processing_time,
            memory_usage=memory_usage
        )
    
    def _parse_html_streaming(self, html_content: str, date: str) -> Tuple[List[Dict], Dict]:
        """Parse HTML with memory-efficient streaming approach."""
        from parse_grid import parse_grid_html
        
        # Parse HTML (this creates temporary objects)
        crew_list, appliance_dict = parse_grid_html(html_content, date)
        
        # Process crew data in place to reduce memory
        processed_crew = []
        for crew in crew_list:
            # Only keep essential data, discard temporary parsing artifacts
            essential_crew = {
                'name': crew['name'],
                'availability': crew['availability']
            }
            processed_crew.append(essential_crew)
        
        # Clear original data structures
        del crew_list
        
        return processed_crew, appliance_dict
    
    def store_batch_data(self, batch: ProcessingBatch) -> bool:
        """Store batch data to database efficiently."""
        try:
            db_pool = get_database_pool()
            
            with db_pool.get_connection() as conn:
                # Use the optimized batch insert operations
                if batch.crew_data:
                    from db_store import insert_crew_availability
                    insert_crew_availability(batch.crew_data, conn)
                
                if batch.appliance_data:
                    from db_store import insert_appliance_availability
                    insert_appliance_availability(batch.appliance_data, conn)
            
            logger.debug(f"Stored batch data: {len(batch.crew_data)} crew, {len(batch.appliance_data)} appliances")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store batch data: {e}")
            return False
    
    def run_optimized_scrape(self, session, max_days: int, cache_minutes_map: Dict[str, int]) -> Dict[str, Any]:
        """Run the optimized scraping process."""
        start_time = time.time()
        today = datetime.now()
        
        self.stats['total_dates'] = max_days
        self.stats['processed_dates'] = 0
        self.stats['failed_dates'] = 0
        self.stats['batch_count'] = 0
        
        logger.info(f"Starting optimized scrape: {max_days} days, batch size {self.batch_size}")
        
        # Initialize database
        from db_store import init_db
        init_db()
        
        # Process dates in batches
        for batch_dates in self.generate_date_batches(today, max_days):
            self.stats['batch_count'] += 1
            
            logger.info(f"Processing batch {self.stats['batch_count']}: {len(batch_dates)} dates")
            
            # Process the batch
            batch = self.process_date_batch(session, batch_dates, cache_minutes_map)
            
            # Store results
            success = self.store_batch_data(batch)
            if not success:
                logger.error(f"Failed to store batch {self.stats['batch_count']}")
            
            # Memory management
            if self.should_force_gc():
                self.cleanup_memory()
            
            # Progress reporting
            progress = (self.stats['processed_dates'] / self.stats['total_dates']) * 100
            logger.info(f"Progress: {progress:.1f}% ({self.stats['processed_dates']}/{self.stats['total_dates']})")
        
        # Final cleanup
        self.cleanup_memory()
        
        total_time = time.time() - start_time
        
        # Generate final report
        return {
            'total_time': total_time,
            'stats': self.stats.copy(),
            'avg_batch_time': total_time / self.stats['batch_count'] if self.stats['batch_count'] > 0 else 0,
            'success_rate': (self.stats['processed_dates'] / self.stats['total_dates']) * 100 if self.stats['total_dates'] > 0 else 0
        }

def run_memory_optimized_scraper(max_days: int, cache_mode: str = "cache-preferred") -> Dict[str, Any]:
    """
    Run the memory-optimized scraper with intelligent batch processing.
    
    Args:
        max_days: Number of days to scrape
        cache_mode: Cache strategy to use
    
    Returns:
        Dictionary with scraping results and performance metrics
    """
    from gartan_fetch import gartan_login_and_get_session
    from config import config
    
    # Get authenticated session (uses session manager)
    session = gartan_login_and_get_session()
    
    # Create cache minutes map
    cache_minutes_map = {}
    for day_offset in range(max_days):
        cache_minutes_map[
            (datetime.now() + timedelta(days=day_offset)).strftime("%d/%m/%Y")
        ] = config.get_cache_minutes(day_offset)
    
    # Create and run optimized scraper
    scraper = MemoryEfficientScraper(
        batch_size=5,  # Process 5 days at a time
        max_workers=3,  # Limit concurrent operations
        memory_limit_mb=400  # Trigger cleanup at 400MB
    )
    
    results = scraper.run_optimized_scrape(session, max_days, cache_minutes_map)
    
    # Cache cleanup
    scraper.cache_manager.cleanup_expired_cache(max_age_days=30)
    
    return results

# Additional memory utilities
import time

def monitor_memory_usage(func):
    """Decorator to monitor memory usage of functions."""
    def wrapper(*args, **kwargs):
        try:
            import psutil
            process = psutil.Process()
            
            # Before
            mem_before = process.memory_info().rss
            start_time = time.time()
            
            # Execute function
            result = func(*args, **kwargs)
            
            # After
            mem_after = process.memory_info().rss
            end_time = time.time()
            
            # Report
            mem_diff = mem_after - mem_before
            duration = end_time - start_time
            
            logger.debug(f"{func.__name__}: {duration:.3f}s, memory: {mem_diff/1024/1024:.1f}MB change")
            
            return result
            
        except ImportError:
            # psutil not available, just run function
            return func(*args, **kwargs)
    
    return wrapper
