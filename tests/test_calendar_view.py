from datetime import date

from src.calendar_view import build_calendar_print_data


def _find_day_cell(calendar_data, target_date: date):
    for month in calendar_data["months"]:
        for week in month["weeks"]:
            for day in week["days"]:
                if day["date"] == target_date:
                    return day
    raise AssertionError(f"Day cell not found: {target_date}")


def test_build_calendar_print_data_expands_night_and_day_assignments():
    schedule = {
        "day": {
            date(2026, 2, 22): {1: "A", 2: "B"},
            date(2026, 3, 1): {3: "C"},
        },
        "night": {
            date(2026, 2, 23): {1: "N1", 2: "N2"},
        },
    }
    ng_dates = {
        "global": ["2026-02-22"],
        "by_member": {"A": ["2026-02-22"], "X": ["2026-02-24"]},
        "by_period": {
            "B": [{"start": "2026-02-24", "end": "2026-02-25", "reason": "休暇"}]
        },
    }

    result = build_calendar_print_data(
        schedule,
        ng_dates,
        start_date=date(2026, 2, 21),
        end_date=date(2026, 3, 20),
        today=date(2026, 2, 21),
    )

    assert [m["label"] for m in result["months"]] == ["2026年2月", "2026年3月"]

    day_0222 = _find_day_cell(result, date(2026, 2, 22))
    assert day_0222["has_global_ng"] is True
    assert day_0222["day_assignments"] == [{"index": 1, "member": "A"}, {"index": 2, "member": "B"}]
    assert day_0222["night_members"] == []
    assert day_0222["member_ng_members"] == ["A"]

    day_0224 = _find_day_cell(result, date(2026, 2, 24))
    assert day_0224["night_members"] == ["N1", "N2"]
    assert day_0224["member_ng_members"] == ["B", "X"]
    assert "B" in day_0224["member_ng_preview"]

    day_0301 = _find_day_cell(result, date(2026, 3, 1))
    assert day_0301["day_assignments"] == [{"index": 3, "member": "C"}]
    assert day_0301["night_members"] == ["N1", "N2"]


def test_build_calendar_print_data_filters_ng_lists_by_target_range():
    schedule = {"day": {}, "night": {}}
    ng_dates = {
        "global": ["2026-01-10", "2026-02-24"],
        "by_member": {
            "A": ["2026-01-10", "2026-02-24", "2026-03-30"],
            "B": ["2026-02-25"],
        },
        "by_period": {
            "A": [{"start": "2026-02-20", "end": "2026-02-28", "reason": "出張"}],
            "B": [{"start": "2026-03-01", "end": "2026-03-10", "reason": "研修"}],
        },
    }

    result = build_calendar_print_data(
        schedule,
        ng_dates,
        start_date=date(2026, 2, 21),
        end_date=date(2026, 2, 28),
    )

    assert result["global_ng_dates"] == [date(2026, 2, 24)]
    assert result["member_ng_rows"] == [
        {"member": "A", "count": 1, "dates": [date(2026, 2, 24)]},
        {"member": "B", "count": 1, "dates": [date(2026, 2, 25)]},
    ]
    assert result["period_ng_rows"] == [
        {"member": "A", "start": date(2026, 2, 20), "end": date(2026, 2, 28), "reason": "出張"}
    ]


def test_build_calendar_print_data_ignores_invalid_ng_data():
    schedule = {"day": {}, "night": {}}
    ng_dates = {
        "global": ["bad-date"],
        "by_member": {"A": ["invalid"]},
        "by_period": {"A": [{"start": "bad", "end": "2026-02-28"}]},
    }

    result = build_calendar_print_data(
        schedule,
        ng_dates,
        start_date=date(2026, 2, 21),
        end_date=date(2026, 2, 28),
    )

    assert result["global_ng_dates"] == []
    assert result["member_ng_rows"] == []
    assert result["period_ng_rows"] == []
    assert result["daily_ng_rows"] == []
