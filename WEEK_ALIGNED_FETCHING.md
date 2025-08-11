# Week-Aligned Data Fetching Implementation

## Issue Addressed

The weekly availability tracking API endpoints require data going back to Monday of the current week. Previously, the bot only fetched data from "today" onwards, which meant:

- If run on Wednesday, it would miss Monday-Tuesday data needed for weekly calculations
- Weekly availability hours would be incomplete or incorrect
- Data gaps could occur if the bot wasn't run regularly

## Solution

Implemented **week-aligned data fetching** that ensures complete weekly data coverage:

### Key Changes

1. **New Function**: `get_week_aligned_date_range()` in `utils.py`
   - Calculates start date as Monday 00:00:00 of current week
   - Adjusts effective max_days to cover historic + future requirements
   - Ensures minimum coverage through next Sunday

2. **Updated Bot Logic** in `run_bot.py`:
   - Uses week-aligned start date instead of "today"
   - Adjusts cache expiry calculation for historic dates
   - Updates progress reporting for effective date range

3. **Smart Date Range Calculation**:
   - **Historic Days**: Monday of current week → Today
   - **Future Days**: Today → Today + max_days
   - **Minimum Coverage**: Always through end of current week

### Example Behavior

**Before** (running on Wednesday with max_days=3):
```
Fetches: Wed, Thu, Fri (3 days)
Missing: Mon, Tue data for weekly calculations ❌
```

**After** (running on Wednesday with max_days=3):
```
Fetches: Mon, Tue, Wed, Thu, Fri, Sat (6 days total)
Coverage: 2 historic + 4 future days ✅
Complete: Full weekly data available
```

### Cache Intelligence

The implementation maintains intelligent caching:
- **Historic dates**: Use appropriate cache duration based on age
- **Today**: 15 minutes cache
- **Future dates**: 1+ hour cache
- **Cache calculation**: Based on actual date, not offset

### CLI Impact

Updated `--max-days` parameter documentation:
- Still controls forward-looking days from today
- Automatically includes historic days back to Monday
- Total fetched days = historic_days + max_days (minimum: full week)

## Benefits

✅ **Complete Weekly Data**: Always have data from Monday onwards  
✅ **Accurate Weekly Calculations**: No missing data gaps  
✅ **Backward Compatible**: Existing workflows continue working  
✅ **Efficient**: Only fetches additional historic days when needed  
✅ **Reliable**: Works regardless of when bot is run during week  

## Files Modified

- `utils.py`: Added `get_week_aligned_date_range()` function
- `run_bot.py`: Updated main fetching loop to use week-aligned dates
- `cli.py`: Updated help text for `--max-days` parameter

## Testing

Created comprehensive tests demonstrating:
- Correct Monday start date calculation
- Proper historic/future day balance
- Cache duration handling for historic dates
- Progress reporting accuracy

The week-aligned fetching ensures the weekly availability API endpoints always have complete, accurate data for reliable workforce planning analytics.
