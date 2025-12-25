# Update History

## 2025-12-25
- Added `ScheduleAnalyzer` for post-generation schedule analysis.
- Updated `schedule_result.html` to display analysis results:
    - Overlap warnings (Day vs Night).
    - Close interval warnings (within 7 days).
    - Assignment counts: Displaying "Current (New)" and "Recent (Last 2 months)".
- **Fixed Night Shift Counting**:
    - Updated `src/data_loader.py` to count consecutive night shift days (e.g. 7 days) as **1 assignment** instead of 7.
    - This aligns the "Past/Recent" count logic with the "Current" count logic (where 1 week = 1 count).
