from datetime import date

from src.ng_status_view import build_ng_status_for_schedule


def test_day_row_contains_global_member_and_period_labels():
    schedule = {
        "day": {
            date(2026, 1, 10): {1: "A", 2: "B", 3: "C"},
        },
        "night": {},
    }
    ng_dates = {
        "global": ["2026-01-10"],
        "by_member": {
            "A": ["2026-01-10"],
        },
        "by_period": {
            "B": [{"start": "2026-01-09", "end": "2026-01-11", "reason": "休暇"}],
        },
    }

    result = build_ng_status_for_schedule(schedule, ng_dates)
    row = result["day"]["2026-01-10"]

    assert row["has_ng"] is True
    assert row["has_member_conflict"] is True
    assert {"kind": "global", "text": "全体NG"} in row["labels"]
    assert {"kind": "member", "text": "A: 個別NG"} in row["labels"]
    assert {"kind": "period", "text": "B: 休暇"} in row["labels"]
    assert result["summary"]["day"]["ng_rows"] == 1
    assert result["summary"]["day"]["member_conflict_rows"] == 1


def test_night_row_expands_week_for_ng_checks():
    schedule = {
        "day": {},
        "night": {
            date(2026, 1, 12): {1: "A", 2: "B"},
        },
    }
    ng_dates = {
        "global": ["2026-01-13"],
        "by_member": {
            "A": ["2026-01-14"],
        },
        "by_period": {
            "B": [{"start": "2026-01-10", "end": "2026-01-12", "reason": "出張"}],
        },
    }

    result = build_ng_status_for_schedule(schedule, ng_dates)
    row = result["night"]["2026-01-12"]
    labels_text = [item["text"] for item in row["labels"]]

    assert row["has_ng"] is True
    assert row["has_member_conflict"] is True
    assert any(text.startswith("全体NG(1/13)") for text in labels_text)
    assert any(text.startswith("A: 個別NG(1/14)") for text in labels_text)
    assert "B: 出張" in labels_text
    assert result["summary"]["night"]["ng_rows"] == 1
    assert result["summary"]["night"]["member_conflict_rows"] == 1


def test_invalid_ng_values_are_ignored():
    schedule = {
        "day": {
            date(2026, 2, 1): {1: "A"},
        },
        "night": {},
    }
    ng_dates = {
        "global": ["invalid-date"],
        "by_member": {"A": ["not-a-date"]},
        "by_period": {"A": [{"start": "bad", "end": "2026-02-02"}]},
    }

    result = build_ng_status_for_schedule(schedule, ng_dates)
    row = result["day"]["2026-02-01"]

    assert row["has_ng"] is False
    assert row["has_member_conflict"] is False
    assert row["labels"] == []


def test_day_row_shows_setting_ng_even_when_assignee_has_no_conflict():
    schedule = {
        "day": {
            date(2026, 2, 1): {1: "Assigned"},
        },
        "night": {},
    }
    ng_dates = {
        "global": [],
        "by_member": {"Other": ["2026-02-01"]},
        "by_period": {},
    }

    result = build_ng_status_for_schedule(schedule, ng_dates)
    row = result["day"]["2026-02-01"]

    assert row["has_ng"] is True
    assert row["has_member_conflict"] is False
    assert any(
        label["kind"] == "setting" and "設定NG" in label["text"]
        for label in row["labels"]
    )


def test_night_row_shows_setting_ng_for_week_range():
    schedule = {
        "day": {},
        "night": {
            date(2026, 2, 2): {1: "Assigned1", 2: "Assigned2"},
        },
    }
    ng_dates = {
        "global": [],
        "by_member": {"Other": ["2026-02-05"]},
        "by_period": {},
    }

    result = build_ng_status_for_schedule(schedule, ng_dates)
    row = result["night"]["2026-02-02"]

    assert row["has_ng"] is True
    assert row["has_member_conflict"] is False
    assert any(
        label["kind"] == "setting" and "設定NG" in label["text"]
        for label in row["labels"]
    )
