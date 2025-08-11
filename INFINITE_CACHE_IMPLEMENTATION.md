# Infinite Cache for Historic Data Implementation

## Problem Addressed

Previously, all cached data had time-based expiry regardless of whether it was historic or current/future data. This meant:

- Historic data (already occurred) would be unnecessarily refetched
- Increased network requests and processing time
- Slower bot startup when re-running
- Potential inconsistency if historic data changed on server (which shouldn't happen)

## Solution

Implemented **infinite cache for historic data** - data from dates that have already passed never expires from cache.

### Key Principle

> **Historic data never changes** - once a day has passed, the availability data for that day is final and should never be refetched.

## Implementation Details

### 1. Updated Cache Duration Logic (`config.py`)

```python
def get_cache_minutes(self, day_offset: int) -> int:
    """
    Get cache expiry minutes based on day offset from today.
    
    Args:
        day_offset: Days relative to today (negative = historic, 0 = today, positive = future)
        
    Returns:
        Cache expiry minutes (or -1 for infinite cache for historic data)
    """
    if day_offset < 0:  # Historic data - never expires
        return -1  # Special value indicating infinite cache
    elif day_offset == 0:  # Today
        return 15  # 15 minutes
    elif day_offset == 1:  # Tomorrow
        return 60  # 1 hour
    else:  # Future days
        return 60 * 24  # 24 hours
```

### 2. Enhanced Cache Validation (`gartan_fetch.py`)

```python
def _is_cache_valid(cache_file: str, cache_minutes: int) -> bool:
    """
    Check if the cache file exists and is not expired.
    
    Args:
        cache_file: Path to cache file
        cache_minutes: Cache expiry in minutes (-1 = infinite cache for historic data)
        
    Returns:
        True if cache is valid and should be used
    """
    if not os.path.exists(cache_file):
        return False
    
    # Historic data with infinite cache
    if cache_minutes == -1:
        return True
    
    # Time-based cache expiry for current/future data
    mtime = os.path.getmtime(cache_file)
    if (dt.now() - dt.fromtimestamp(mtime)).total_seconds() / 60 < cache_minutes:
        return True
    return False
```

### 3. Week-Aligned Integration

Works seamlessly with week-aligned fetching:
- Historic days (Monday to yesterday): Infinite cache
- Today: 15-minute cache
- Future days: 1-24 hour cache based on distance

## Cache Strategy Examples

**Running on Sunday (today = 2025-08-10) with max_days=3:**

| Date        | Days from Today | Cache Strategy      |
|-------------|-----------------|---------------------|
| 08/04 (Mon) | -6              | Infinite (historic) |
| 08/05 (Tue) | -5              | Infinite (historic) |
| 08/06 (Wed) | -4              | Infinite (historic) |
| 08/07 (Thu) | -3              | Infinite (historic) |
| 08/08 (Fri) | -2              | Infinite (historic) |
| 08/09 (Sat) | -1              | Infinite (historic) |
| 08/10 (Sun) | 0               | 15 minutes          |
| 08/11 (Mon) | 1               | 60 minutes          |
| 08/12 (Tue) | 2               | 1440 minutes (24h)  |

## Performance Benefits

### Network Optimization
- **Reduced Requests**: Historic data fetched once, used forever
- **Faster Startup**: Bot starts quickly with cached historic data
- **Bandwidth Savings**: No unnecessary refetching of unchanging data

### Reliability Benefits
- **Consistent Data**: Historic availability never changes unexpectedly
- **Offline Capability**: Can work with cached historic data when offline
- **Predictable Behavior**: Cache hits vs misses are deterministic

### Example Impact

**Before** (running bot daily for a week):
- Day 1: Fetch 7 days (7 requests)
- Day 2: Fetch 7 days (7 requests) - refetches yesterday unnecessarily
- Day 3: Fetch 7 days (7 requests) - refetches 2 historic days
- **Total**: 21 requests, many unnecessary

**After** (with infinite historic cache):
- Day 1: Fetch 7 days (7 requests)
- Day 2: Fetch 1 new day (1 request) - reuses yesterday's cache
- Day 3: Fetch 1 new day (1 request) - reuses all historic cache
- **Total**: 9 requests, 57% reduction

## Testing

Comprehensive test suite covers:
- ✅ Infinite cache for negative day offsets
- ✅ Time-based cache for current/future dates
- ✅ Cache validation logic with -1 special value
- ✅ Integration with week-aligned date ranges
- ✅ File existence checking

## Backward Compatibility

- ✅ Existing cache files continue to work
- ✅ No changes to cache file formats
- ✅ Graceful handling of missing cache files
- ✅ Same API for cache functions

## Files Modified

- `config.py`: Updated `get_cache_minutes()` to return -1 for historic data
- `gartan_fetch.py`: Enhanced `_is_cache_valid()` to handle infinite cache
- `run_bot.py`: Added debug logging for cache strategy
- `tests/test_infinite_cache.py`: Comprehensive test suite

The infinite cache implementation significantly improves performance and reliability while maintaining backward compatibility and working seamlessly with the weekly availability tracking system.
