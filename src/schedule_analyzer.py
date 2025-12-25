
from datetime import date, timedelta
from typing import Dict, List, Any, Optional

class ScheduleAnalyzer:
    """
    Generated Schedule Analyzer
    Checks for overlaps, close intervals, and calculates assignment counts.
    """

    def __init__(self, schedule: Dict, member_stats: Dict = None):
        """
        Args:
            schedule: The generated schedule dict {'day': {...}, 'night': {...}}
            member_stats: Historical stats (optional)
        """
        self.schedule = schedule
        self.member_stats = member_stats or {}
        self.analysis_result = {
            "overlaps": [],
            "close_intervals": [],
            "member_counts": []
        }

    def analyze(self) -> Dict[str, Any]:
        """Run all analyses"""
        self._check_overlaps()
        self._check_close_intervals()
        self._calculate_counts()
        return self.analysis_result

    def _check_overlaps(self):
        """
        Check if a member is assigned to both Day and Night shifts 
        where the Day shift falls within the Night shift week.
        """
        day_schedule = self.schedule.get('day', {})
        night_schedule = self.schedule.get('night', {})

        # Iterate through Night shifts (by week)
        for night_start, night_assigns in night_schedule.items():
            night_end = night_start + timedelta(days=6)
            
            # Check each member in this night shift
            for n_idx, n_member in night_assigns.items():
                
                # Check Day shifts within this week
                for d_date, d_assigns in day_schedule.items():
                    if night_start <= d_date <= night_end:
                        for d_idx, d_member in d_assigns.items():
                            if n_member == d_member:
                                self.analysis_result["overlaps"].append({
                                    "member": n_member,
                                    "date": d_date,
                                    "details": f"Night (Week of {night_start}) & Day ({d_date})"
                                })

    def _check_close_intervals(self, threshold_days=7):
        """
        Check for assignments within threshold_days of each other.
        Considers:
        - Day to Day
        - Day to Night
        - Night to Day
        - Night to Night
        """
        # 1. Collect all assignments per member
        # Format: {'start': date, 'end': date, 'type': 'day'|'night'}
        member_assignments = {}

        # Collect Day assignments
        for d_date, assigns in self.schedule.get('day', {}).items():
            for idx, member in assigns.items():
                if member not in member_assignments:
                    member_assignments[member] = []
                member_assignments[member].append({
                    'start': d_date,
                    'end': d_date,
                    'type': 'day',
                    'desc': f"日勤({d_date})"
                })

        # Collect Night assignments
        for n_start, assigns in self.schedule.get('night', {}).items():
            n_end = n_start + timedelta(days=6)
            for idx, member in assigns.items():
                if member not in member_assignments:
                    member_assignments[member] = []
                member_assignments[member].append({
                    'start': n_start,
                    'end': n_end,
                    'type': 'night',
                    'desc': f"夜勤({n_start}週)"
                })

        # 2. Sort and check intervals
        for member, assignments in member_assignments.items():
            # Sort by start date
            assignments.sort(key=lambda x: x['start'])
            
            for i in range(len(assignments) - 1):
                current = assignments[i]
                next_assign = assignments[i+1]
                
                # Gap calculation: Next Start - Current End
                gap = (next_assign['start'] - current['end']).days
                
                # Since day shift end is same as start, gap 1 means consecutive days (e.g. Sat -> Sun)
                # gap > 0 means there is at least 1 day in between? 
                # e.g. Sat (End Sat) -> Sun (Start Sun). Sun - Sat = 1. Gap is 1 day (0 days in between).
                # User asks for "within 7 days" (assuming interval < 7)
                
                # Logic: If I work on 1st, and next is 8th. 8-1 = 7. Gap is 7.
                # If "within 7 days" means gap < 7 (i.e. 1..6 days apart)
                
                if 0 < gap <= threshold_days:
                     self.analysis_result["close_intervals"].append({
                        "member": member,
                        "gap": gap,
                        "from": current['desc'],
                        "to": next_assign['desc']
                    })
                elif gap <= 0:
                     # This is effectively an overlap or consecutive/same day which might be caught by overlap check
                     # But for Day-Day consecutive (Sat/Sun), it's common but maybe worth noting if user wants strict checks.
                     # However, user specifically asked for "Overlap Day/Night".
                     # Close interval usually implies "too close".
                     pass

    def _calculate_counts(self):
        """
        Calculate total counts for each member (Past + New)
        """
        counts = {}
        
        # Initialize with known members from stats or schedule
        all_members = set(self.member_stats.keys())
        
        # Add members from current schedule
        for s_type in ['day', 'night']:
            for date_key, assigns in self.schedule.get(s_type, {}).items():
                for member in assigns.values():
                    all_members.add(member)

        for member in all_members:
            # Past counts
            past_day = 0
            past_night = 0
            if member in self.member_stats:
                past_day = self.member_stats[member].get('day_count', 0)
                past_night = self.member_stats[member].get('night_count', 0)
            
            # New counts
            new_day = 0
            new_night = 0
            
            # Count Day
            for assigns in self.schedule.get('day', {}).values():
                for m in assigns.values():
                    if m == member:
                        new_day += 1
            
            # Count Night
            for assigns in self.schedule.get('night', {}).values():
                for m in assigns.values():
                    if m == member:
                        new_night += 1
            
            counts[member] = {
                "total_day": past_day + new_day,
                "total_night": past_night + new_night,
                "new_day": new_day,
                "new_night": new_night,
                "past_day": past_day,
                "past_night": past_night
            }
            
        # Convert to list for easy template iteration
        result_list = []
        for member, stats in counts.items():
            # Filter out members with 0 counts if desired, or keep all
            if stats['total_day'] > 0 or stats['total_night'] > 0:
                result_list.append({
                    "name": member,
                    **stats
                })
        
        # Sort by Name
        result_list.sort(key=lambda x: x['name'])
        self.analysis_result["member_counts"] = result_list

