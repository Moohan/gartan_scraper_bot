"""
Enhanced cache management with smart warming and batch operations.

Provides intelligent cache warming, batch cache operations, and optimized
cache strategies for improved performance.
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
import concurrent.futures
from logging_config import get_logger

logger = get_logger()

class SmartCacheManager:
    """Intelligent cache management with predictive warming and batch operations."""
    
    def __init__(self, cache_dir: str = "_cache", max_workers: int = 3):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_workers = max_workers
        self._cache_info = {}  # Cache metadata
        self._cache_lock = threading.Lock()
        
    def get_cache_file_path(self, booking_date: str) -> Path:
        """Get the cache file path for a booking date."""
        cache_filename = f"grid_{booking_date.replace('/', '-')}.html"
        return self.cache_dir / cache_filename
    
    def is_cache_valid(self, booking_date: str, cache_minutes: int) -> bool:
        """Check if cache is valid and not expired."""
        cache_file = self.get_cache_file_path(booking_date)
        
        if not cache_file.exists():
            return False
            
        # Check file modification time
        mtime = cache_file.stat().st_mtime
        age_minutes = (time.time() - mtime) / 60
        
        return age_minutes < cache_minutes
    
    def read_cache(self, booking_date: str) -> Optional[str]:
        """Read cache content with error handling."""
        cache_file = self.get_cache_file_path(booking_date)
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug(f"Cache hit for {booking_date}")
            return content
        except (FileNotFoundError, UnicodeDecodeError, IOError) as e:
            logger.debug(f"Cache read failed for {booking_date}: {e}")
            return None
    
    def write_cache(self, booking_date: str, content: str) -> bool:
        """Write content to cache with error handling."""
        cache_file = self.get_cache_file_path(booking_date)
        
        try:
            # Ensure directory exists
            cache_file.parent.mkdir(exist_ok=True)
            
            # Write to temporary file first, then rename for atomicity
            temp_file = cache_file.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Atomic rename
            temp_file.replace(cache_file)
            logger.debug(f"Cache written for {booking_date}")
            return True
            
        except IOError as e:
            logger.error(f"Cache write failed for {booking_date}: {e}")
            return False
    
    def batch_cache_check(self, booking_dates: List[str], cache_minutes: int) -> Dict[str, bool]:
        """Check cache validity for multiple dates efficiently."""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_date = {
                executor.submit(self.is_cache_valid, date, cache_minutes): date
                for date in booking_dates
            }
            
            for future in concurrent.futures.as_completed(future_to_date):
                date = future_to_date[future]
                try:
                    results[date] = future.result()
                except Exception as e:
                    logger.error(f"Cache check failed for {date}: {e}")
                    results[date] = False
        
        return results
    
    def get_cache_strategy(self, booking_date: str, cache_minutes: int) -> str:
        """Determine optimal cache strategy based on date and current cache state."""
        try:
            date_obj = datetime.strptime(booking_date, "%d/%m/%Y")
            today = datetime.now().date()
            days_diff = (date_obj.date() - today).days
            
            # Strategy based on how far in the future the date is
            if days_diff < 0:
                return "cache-first"  # Past dates rarely change
            elif days_diff == 0:
                return "cache-preferred"  # Today changes frequently
            elif days_diff <= 7:
                return "cache-preferred"  # Near future, moderate changes
            else:
                return "cache-first"  # Far future, infrequent changes
                
        except ValueError:
            return "cache-preferred"  # Default fallback
    
    def warm_cache_batch(self, session, booking_dates: List[str], 
                        cache_minutes_map: Dict[str, int]) -> Dict[str, str]:
        """
        Warm cache for multiple dates using intelligent batching.
        Returns dict of date -> content for successful cache operations.
        """
        from gartan_fetch import fetch_grid_html_for_date
        
        # Check which dates need cache refresh
        cache_validity = {}
        for date in booking_dates:
            cache_min = cache_minutes_map.get(date, 15)
            cache_validity[date] = self.is_cache_valid(date, cache_min)
        
        dates_to_fetch = [date for date, valid in cache_validity.items() if not valid]
        logger.debug(f"Cache warming: {len(dates_to_fetch)} of {len(booking_dates)} dates need refresh")
        
        results = {}
        
        # Read valid cache entries
        for date in booking_dates:
            if cache_validity[date]:
                content = self.read_cache(date)
                if content:
                    results[date] = content
        
        # Batch fetch missing/expired entries with controlled concurrency
        if dates_to_fetch:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit fetch tasks with delay to avoid overwhelming server
                future_to_date = {}
                for i, date in enumerate(dates_to_fetch):
                    future = executor.submit(self._fetch_and_cache_with_delay, 
                                           session, date, i * 0.5)  # 500ms delay between requests
                    future_to_date[future] = date
                
                # Collect results
                for future in concurrent.futures.as_completed(future_to_date):
                    date = future_to_date[future]
                    try:
                        content = future.result()
                        if content:
                            results[date] = content
                    except Exception as e:
                        logger.error(f"Batch fetch failed for {date}: {e}")
        
        logger.debug(f"Cache warming completed: {len(results)} dates successfully cached")
        return results
    
    def _fetch_and_cache_with_delay(self, session, date: str, delay: float) -> Optional[str]:
        """Fetch content with delay and cache it."""
        from gartan_fetch import fetch_grid_html_for_date
        
        if delay > 0:
            time.sleep(delay)
        
        try:
            content = fetch_grid_html_for_date(session, date)
            if content:
                self.write_cache(date, content)
                return content
        except Exception as e:
            logger.error(f"Fetch and cache failed for {date}: {e}")
        
        return None
    
    def cleanup_expired_cache(self, max_age_days: int = 30) -> int:
        """Clean up old cache files and return count of files removed."""
        if not self.cache_dir.exists():
            return 0
        
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        removed_count = 0
        
        for cache_file in self.cache_dir.glob("grid_*.html"):
            try:
                if cache_file.stat().st_mtime < cutoff_time:
                    cache_file.unlink()
                    removed_count += 1
                    logger.debug(f"Removed expired cache file: {cache_file.name}")
            except OSError as e:
                logger.warning(f"Failed to remove cache file {cache_file}: {e}")
        
        logger.debug(f"Cache cleanup: removed {removed_count} expired files")
        return removed_count
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        if not self.cache_dir.exists():
            return {"total_files": 0, "total_size": 0}
        
        total_files = 0
        total_size = 0
        
        for cache_file in self.cache_dir.glob("grid_*.html"):
            try:
                stat = cache_file.stat()
                total_files += 1
                total_size += stat.st_size
            except OSError:
                continue
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "cache_dir": str(self.cache_dir)
        }

# Global cache manager instance
_cache_manager = None

def get_cache_manager(cache_dir: str = "_cache") -> SmartCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None or str(_cache_manager.cache_dir) != cache_dir:
        _cache_manager = SmartCacheManager(cache_dir)
        logger.debug(f"Initialized smart cache manager for {cache_dir}")
    return _cache_manager
