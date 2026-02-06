"""
結果画面向けのNG情報可視化データを生成するモジュール。
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Set, Tuple


def build_ng_status_for_schedule(
    schedule: Dict[str, Dict[date, Dict[int, str]]],
    ng_dates: Dict[str, Any],
) -> Dict[str, Any]:
    """スケジュールとNG設定から、結果画面で使う表示用データを作る。"""
    global_dates = _parse_date_set(ng_dates.get("global", []))
    by_member_dates = {
        member: _parse_date_set(dates)
        for member, dates in ng_dates.get("by_member", {}).items()
    }
    by_member_periods = {
        member: _parse_periods(periods)
        for member, periods in ng_dates.get("by_period", {}).items()
    }

    day_rows, day_summary = _build_day_rows(
        schedule.get("day", {}),
        global_dates,
        by_member_dates,
        by_member_periods,
    )
    night_rows, night_summary = _build_night_rows(
        schedule.get("night", {}),
        global_dates,
        by_member_dates,
        by_member_periods,
    )

    return {
        "day": day_rows,
        "night": night_rows,
        "summary": {
            "day": day_summary,
            "night": night_summary,
        },
    }


def _build_day_rows(
    day_schedule: Dict[date, Dict[int, str]],
    global_dates: Set[date],
    by_member_dates: Dict[str, Set[date]],
    by_member_periods: Dict[str, List[Dict[str, Any]]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
    rows: Dict[str, Dict[str, Any]] = {}
    ng_count = 0
    member_conflict_count = 0

    for target_date, indexes in day_schedule.items():
        row_key = target_date.isoformat()
        labels: List[Dict[str, str]] = []
        has_member_conflict = False
        members_with_ng = _collect_ng_members_for_date(
            target_date, by_member_dates, by_member_periods
        )

        if members_with_ng:
            labels.append(
                {
                    "kind": "setting",
                    "text": _format_setting_member_label(members_with_ng),
                }
            )

        if target_date in global_dates:
            labels.append({"kind": "global", "text": "全体NG"})

        for member in _unique_members(indexes):
            if target_date in by_member_dates.get(member, set()):
                labels.append(
                    {"kind": "member", "text": f"{member}: 個別NG"}
                )
                has_member_conflict = True

            for period in by_member_periods.get(member, []):
                if period["start"] <= target_date <= period["end"]:
                    reason = period.get("reason") or "期間NG"
                    labels.append(
                        {"kind": "period", "text": f"{member}: {reason}"}
                    )
                    has_member_conflict = True

        has_ng = len(labels) > 0
        if has_ng:
            ng_count += 1
        if has_member_conflict:
            member_conflict_count += 1

        rows[row_key] = {
            "labels": labels,
            "has_ng": has_ng,
            "has_member_conflict": has_member_conflict,
        }

    summary = {
        "total_rows": len(day_schedule),
        "ng_rows": ng_count,
        "member_conflict_rows": member_conflict_count,
    }
    return rows, summary


def _build_night_rows(
    night_schedule: Dict[date, Dict[int, str]],
    global_dates: Set[date],
    by_member_dates: Dict[str, Set[date]],
    by_member_periods: Dict[str, List[Dict[str, Any]]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
    rows: Dict[str, Dict[str, Any]] = {}
    ng_count = 0
    member_conflict_count = 0

    for week_start, indexes in night_schedule.items():
        row_key = week_start.isoformat()
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        week_end = week_dates[-1]
        labels: List[Dict[str, str]] = []
        has_member_conflict = False
        members_with_ng = _collect_ng_members_for_range(
            week_start, week_end, by_member_dates, by_member_periods
        )

        if members_with_ng:
            labels.append(
                {
                    "kind": "setting",
                    "text": _format_setting_member_label(members_with_ng),
                }
            )

        global_hits = sorted([d for d in week_dates if d in global_dates])
        if global_hits:
            labels.append(
                {
                    "kind": "global",
                    "text": f"全体NG({_format_date_list(global_hits)})",
                }
            )

        for member in _unique_members(indexes):
            member_hits = sorted(
                [d for d in week_dates if d in by_member_dates.get(member, set())]
            )
            if member_hits:
                labels.append(
                    {
                        "kind": "member",
                        "text": f"{member}: 個別NG({_format_date_list(member_hits)})",
                    }
                )
                has_member_conflict = True

            for period in by_member_periods.get(member, []):
                if period["start"] <= week_end and week_start <= period["end"]:
                    reason = period.get("reason") or "期間NG"
                    labels.append(
                        {"kind": "period", "text": f"{member}: {reason}"}
                    )
                    has_member_conflict = True

        has_ng = len(labels) > 0
        if has_ng:
            ng_count += 1
        if has_member_conflict:
            member_conflict_count += 1

        rows[row_key] = {
            "labels": labels,
            "has_ng": has_ng,
            "has_member_conflict": has_member_conflict,
        }

    summary = {
        "total_rows": len(night_schedule),
        "ng_rows": ng_count,
        "member_conflict_rows": member_conflict_count,
    }
    return rows, summary


def _parse_date_set(values: List[Any]) -> Set[date]:
    parsed: Set[date] = set()
    for item in values:
        try:
            parsed.add(date.fromisoformat(str(item)))
        except (TypeError, ValueError):
            continue
    return parsed


def _parse_periods(periods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed: List[Dict[str, Any]] = []
    for period in periods:
        try:
            start = date.fromisoformat(str(period.get("start")))
            end = date.fromisoformat(str(period.get("end")))
        except (TypeError, ValueError):
            continue

        if start > end:
            continue

        parsed.append(
            {
                "start": start,
                "end": end,
                "reason": (period.get("reason") or "").strip(),
            }
        )
    return parsed


def _unique_members(indexes: Dict[int, str]) -> List[str]:
    members = {member for member in indexes.values() if member}
    return sorted(members)


def _format_date_list(dates: List[date]) -> str:
    return ", ".join([f"{d.month}/{d.day}" for d in dates])


def _format_setting_member_label(members: List[str]) -> str:
    shown = members[:3]
    extra = len(members) - len(shown)
    if extra > 0:
        return f"設定NG: {', '.join(shown)} ほか{extra}名"
    return f"設定NG: {', '.join(shown)}"


def _collect_ng_members_for_date(
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


def _collect_ng_members_for_range(
    start_date: date,
    end_date: date,
    by_member_dates: Dict[str, Set[date]],
    by_member_periods: Dict[str, List[Dict[str, Any]]],
) -> List[str]:
    members = set()

    for member, dates in by_member_dates.items():
        if any(start_date <= d <= end_date for d in dates):
            members.add(member)

    for member, periods in by_member_periods.items():
        for period in periods:
            if period["start"] <= end_date and start_date <= period["end"]:
                members.add(member)
                break

    return sorted(members)
