"""カレンダー表示表示データを生成するモジュール。"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any, Dict, List, Set


DISPLAY_WEEKDAYS_JA = ["日", "月", "火", "水", "木", "金", "土"]


def build_calendar_print_data(
    schedule: Dict[str, Dict[date, Dict[int, str]]],
    ng_dates: Dict[str, Any],
    start_date: date,
    end_date: date,
    *,
    today: date | None = None,
) -> Dict[str, Any]:
    """スケジュールとNG情報をカレンダー表示表示データへ変換する。"""
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    today_date = today or date.today()
    parsed_ng = _parse_ng_dates(ng_dates)

    day_schedule = schedule.get("day", {})
    night_schedule = schedule.get("night", {})
    night_by_date = _expand_night_schedule(night_schedule)

    months = _build_month_blocks(
        day_schedule,
        night_by_date,
        parsed_ng,
        start_date,
        end_date,
        today_date,
    )
    daily_ng_rows = _build_daily_ng_rows(parsed_ng, start_date, end_date)
    member_ng_rows = _build_member_ng_rows(parsed_ng, start_date, end_date)
    period_ng_rows = _build_period_ng_rows(parsed_ng, start_date, end_date)
    global_ng_dates = sorted(
        [d for d in parsed_ng["global_dates"] if start_date <= d <= end_date]
    )

    return {
        "months": months,
        "global_ng_dates": global_ng_dates,
        "member_ng_rows": member_ng_rows,
        "period_ng_rows": period_ng_rows,
        "daily_ng_rows": daily_ng_rows,
    }


def _build_month_blocks(
    day_schedule: Dict[date, Dict[int, str]],
    night_by_date: Dict[date, Dict[str, Any]],
    parsed_ng: Dict[str, Any],
    start_date: date,
    end_date: date,
    today: date,
) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    month_cursor = date(start_date.year, start_date.month, 1)
    calendar_builder = calendar.Calendar(firstweekday=6)

    while month_cursor <= end_date:
        year = month_cursor.year
        month = month_cursor.month
        weeks = []

        for week in calendar_builder.monthdatescalendar(year, month):
            week_cells = [
                _build_day_cell(
                    target_date=target_date,
                    target_month=month,
                    day_schedule=day_schedule,
                    night_by_date=night_by_date,
                    parsed_ng=parsed_ng,
                    start_date=start_date,
                    end_date=end_date,
                    today=today,
                )
                for target_date in week
            ]
            weeks.append({"days": week_cells})

        blocks.append(
            {
                "year": year,
                "month": month,
                "label": f"{year}年{month}月",
                "weeks": weeks,
            }
        )

        if month == 12:
            month_cursor = date(year + 1, 1, 1)
        else:
            month_cursor = date(year, month + 1, 1)

    return blocks


def _build_day_cell(
    *,
    target_date: date,
    target_month: int,
    day_schedule: Dict[date, Dict[int, str]],
    night_by_date: Dict[date, Dict[str, Any]],
    parsed_ng: Dict[str, Any],
    start_date: date,
    end_date: date,
    today: date,
) -> Dict[str, Any]:
    indexes = day_schedule.get(target_date, {})
    day_assignments = []
    for index in [1, 2, 3]:
        member = indexes.get(index)
        if member:
            day_assignments.append({"index": index, "member": member})

    night_info = night_by_date.get(target_date)
    night_members = []
    if night_info:
        for index in [1, 2]:
            member = night_info["indexes"].get(index)
            if member:
                night_members.append(member)

    member_ng_members = _collect_members_unavailable_on_date(
        target_date,
        parsed_ng["by_member_dates"],
        parsed_ng["by_member_periods"],
    )

    return {
        "date": target_date,
        "weekday_label": DISPLAY_WEEKDAYS_JA[(target_date.weekday() + 1) % 7],
        "in_month": target_date.month == target_month,
        "in_range": start_date <= target_date <= end_date,
        "is_today": target_date == today,
        "is_weekend": target_date.weekday() in [5, 6],
        "day_assignments": day_assignments,
        "night_members": night_members,
        "night_week_start": night_info["week_start"] if night_info else None,
        "night_week_end": night_info["week_end"] if night_info else None,
        "has_global_ng": target_date in parsed_ng["global_dates"],
        "member_ng_count": len(member_ng_members),
        "member_ng_preview": _format_member_preview(member_ng_members),
        "member_ng_members": member_ng_members,
    }


def _build_daily_ng_rows(
    parsed_ng: Dict[str, Any],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    rows = []
    cursor = start_date
    while cursor <= end_date:
        is_global_ng = cursor in parsed_ng["global_dates"]
        members = _collect_members_unavailable_on_date(
            cursor,
            parsed_ng["by_member_dates"],
            parsed_ng["by_member_periods"],
        )
        if is_global_ng or members:
            rows.append(
                {
                    "date": cursor,
                    "weekday_label": DISPLAY_WEEKDAYS_JA[(cursor.weekday() + 1) % 7],
                    "is_global_ng": is_global_ng,
                    "members": members,
                }
            )
        cursor += timedelta(days=1)

    return rows


def _build_member_ng_rows(
    parsed_ng: Dict[str, Any],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    rows = []
    by_member_dates: Dict[str, Set[date]] = parsed_ng["by_member_dates"]
    for member, dates in sorted(by_member_dates.items()):
        in_range_dates = sorted([d for d in dates if start_date <= d <= end_date])
        if not in_range_dates:
            continue
        rows.append(
            {
                "member": member,
                "count": len(in_range_dates),
                "dates": in_range_dates,
            }
        )
    return rows


def _build_period_ng_rows(
    parsed_ng: Dict[str, Any],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    rows = []
    by_member_periods: Dict[str, List[Dict[str, Any]]] = parsed_ng["by_member_periods"]
    for member, periods in sorted(by_member_periods.items()):
        for period in periods:
            if period["start"] <= end_date and start_date <= period["end"]:
                rows.append(
                    {
                        "member": member,
                        "start": period["start"],
                        "end": period["end"],
                        "reason": period["reason"] or "期間NG",
                    }
                )

    rows.sort(key=lambda item: (item["start"], item["member"]))
    return rows


def _expand_night_schedule(
    night_schedule: Dict[date, Dict[int, str]],
) -> Dict[date, Dict[str, Any]]:
    expanded: Dict[date, Dict[str, Any]] = {}
    for week_start, indexes in night_schedule.items():
        week_end = week_start + timedelta(days=6)
        for i in range(7):
            target_date = week_start + timedelta(days=i)
            expanded[target_date] = {
                "week_start": week_start,
                "week_end": week_end,
                "indexes": indexes,
            }
    return expanded


def _parse_ng_dates(ng_dates: Dict[str, Any]) -> Dict[str, Any]:
    global_dates = _parse_date_set(ng_dates.get("global", []))
    by_member_dates = {
        member: _parse_date_set(values)
        for member, values in ng_dates.get("by_member", {}).items()
    }
    by_member_periods = {
        member: _parse_periods(values)
        for member, values in ng_dates.get("by_period", {}).items()
    }

    return {
        "global_dates": global_dates,
        "by_member_dates": by_member_dates,
        "by_member_periods": by_member_periods,
    }


def _parse_date_set(values: List[Any]) -> Set[date]:
    parsed: Set[date] = set()
    for item in values:
        try:
            parsed.add(date.fromisoformat(str(item)))
        except (TypeError, ValueError):
            continue
    return parsed


def _parse_periods(values: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    periods = []
    for value in values:
        try:
            start = date.fromisoformat(str(value.get("start")))
            end = date.fromisoformat(str(value.get("end")))
        except (TypeError, ValueError):
            continue
        if start > end:
            continue
        periods.append(
            {
                "start": start,
                "end": end,
                "reason": (value.get("reason") or "").strip(),
            }
        )
    periods.sort(key=lambda item: item["start"])
    return periods


def _collect_members_unavailable_on_date(
    target_date: date,
    by_member_dates: Dict[str, Set[date]],
    by_member_periods: Dict[str, List[Dict[str, Any]]],
) -> List[str]:
    members = set()

    for member, dates in by_member_dates.items():
        if target_date in dates:
            members.add(member)

    for member, periods in by_member_periods.items():
        for period in periods:
            if period["start"] <= target_date <= period["end"]:
                members.add(member)
                break

    return sorted(members)


def _format_member_preview(members: List[str], *, max_names: int = 3) -> str:
    if not members:
        return ""
    preview = members[:max_names]
    if len(members) > max_names:
        return f"{', '.join(preview)} 他{len(members) - max_names}名"
    return ", ".join(preview)
