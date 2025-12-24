"""
日付処理ユーティリティモジュール
"""
from datetime import date, timedelta
from typing import Tuple, List
from dateutil.relativedelta import relativedelta


def get_rotation_period(start_date: date) -> Tuple[date, date]:
    """
    ローテーション期間（21日～2ヶ月後の20日）を計算する

    Args:
        start_date: 開始日（月の21日を想定）

    Returns:
        (開始日, 終了日) のタプル
        例: (2025-03-21, 2025-05-20)
    """
    # 2ヶ月後の20日を計算
    end_date = start_date + relativedelta(months=2) - timedelta(days=1)
    return start_date, end_date


def get_week_range(week_start: date) -> Tuple[date, date]:
    """
    週の開始日から終了日（月曜～日曜の7日間）を計算する

    Args:
        week_start: 週の開始日（月曜日）

    Returns:
        (週開始日, 週終了日) のタプル
    """
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_mondays_in_period(start_date: date, end_date: date) -> List[date]:
    """
    期間内の全ての月曜日を取得する

    Args:
        start_date: 開始日
        end_date: 終了日

    Returns:
        月曜日のリスト
    """
    mondays = []
    current = start_date

    # 最初の月曜日まで進める
    while current.weekday() != 0:  # 0 = 月曜日
        current += timedelta(days=1)
        if current > end_date:
            return mondays

    # 期間内の全ての月曜日を収集
    while current <= end_date:
        mondays.append(current)
        current += timedelta(days=7)

    return mondays


def get_weekends_in_period(start_date: date, end_date: date) -> List[date]:
    """
    期間内の全ての土日を取得する

    Args:
        start_date: 開始日
        end_date: 終了日

    Returns:
        土日のリスト
    """
    weekends = []
    current = start_date

    while current <= end_date:
        if current.weekday() in [5, 6]:  # 5 = 土曜日, 6 = 日曜日
            weekends.append(current)
        current += timedelta(days=1)

    return weekends


def is_weekend(target_date: date) -> bool:
    """
    指定日が土日かどうかを判定する

    Args:
        target_date: 判定対象の日付

    Returns:
        土日の場合True
    """
    return target_date.weekday() in [5, 6]


def get_lookback_period(reference_date: date, months: int) -> Tuple[date, date]:
    """
    参照日から過去N ヶ月間の期間を計算する

    Args:
        reference_date: 基準日
        months: 遡る月数

    Returns:
        (開始日, 終了日) のタプル
    """
    end_date = reference_date
    start_date = reference_date - relativedelta(months=months) + timedelta(days=1)
    return start_date, end_date


def date_range(start_date: date, end_date: date) -> List[date]:
    """
    開始日から終了日までの日付リストを生成する

    Args:
        start_date: 開始日
        end_date: 終了日

    Returns:
        日付のリスト
    """
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates
