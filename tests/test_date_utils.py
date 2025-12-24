"""
date_utils.pyのテスト
"""
import pytest
from datetime import date, timedelta
from utils.date_utils import (
    get_rotation_period,
    get_week_range,
    get_mondays_in_period,
    get_weekends_in_period,
    is_weekend,
    get_lookback_period,
    date_range
)


class TestDateUtils:
    """日付ユーティリティのテスト"""

    def test_get_rotation_period(self):
        """ローテーション期間計算のテスト"""
        # 2025年3月21日から2ヶ月
        start = date(2025, 3, 21)
        expected_start = date(2025, 3, 21)
        expected_end = date(2025, 5, 20)

        actual_start, actual_end = get_rotation_period(start)

        assert actual_start == expected_start
        assert actual_end == expected_end

    def test_get_week_range(self):
        """週の範囲計算のテスト"""
        # 2025年3月24日（月曜日）から
        monday = date(2025, 3, 24)
        expected_start = date(2025, 3, 24)
        expected_end = date(2025, 3, 30)  # 日曜日

        actual_start, actual_end = get_week_range(monday)

        assert actual_start == expected_start
        assert actual_end == expected_end

    def test_get_mondays_in_period(self):
        """期間内の月曜日取得のテスト"""
        start = date(2025, 3, 21)  # 金曜日
        end = date(2025, 4, 20)    # 日曜日

        mondays = get_mondays_in_period(start, end)

        # 最初の月曜日: 3/24
        assert mondays[0] == date(2025, 3, 24)
        # 最後の月曜日: 4/14
        assert mondays[-1] == date(2025, 4, 14)
        # 合計4週分の月曜日 (3/24, 3/31, 4/7, 4/14)
        assert len(mondays) == 4

    def test_get_weekends_in_period(self):
        """期間内の土日取得のテスト"""
        start = date(2025, 3, 21)  # 金曜日
        end = date(2025, 3, 30)    # 日曜日

        weekends = get_weekends_in_period(start, end)

        # 3/22(土), 3/23(日), 3/29(土), 3/30(日)
        assert len(weekends) == 4
        assert date(2025, 3, 22) in weekends  # 土曜日
        assert date(2025, 3, 23) in weekends  # 日曜日

    def test_is_weekend(self):
        """土日判定のテスト"""
        # 土曜日
        saturday = date(2025, 3, 22)
        assert is_weekend(saturday) == True

        # 日曜日
        sunday = date(2025, 3, 23)
        assert is_weekend(sunday) == True

        # 月曜日
        monday = date(2025, 3, 24)
        assert is_weekend(monday) == False

    def test_get_lookback_period(self):
        """過去期間計算のテスト"""
        reference = date(2025, 3, 20)
        months = 2

        start, end = get_lookback_period(reference, months)

        assert end == reference
        # 約2ヶ月前
        assert start == date(2025, 1, 21)

    def test_date_range(self):
        """日付範囲生成のテスト"""
        start = date(2025, 3, 1)
        end = date(2025, 3, 5)

        dates = date_range(start, end)

        assert len(dates) == 5
        assert dates[0] == date(2025, 3, 1)
        assert dates[-1] == date(2025, 3, 5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
