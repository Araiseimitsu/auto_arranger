"""
制約チェッカーのテスト
"""

import pytest
from datetime import date, timedelta
from src.constraint_checker import ConstraintChecker


@pytest.fixture
def sample_settings():
    """テスト用settings"""
    return {
        'constraints': {
            'interval': {
                'min_days_between_same_person_day': 14,
                'min_days_between_same_person_night': 21
            },
            'night_to_day_gap': {
                'min_days': 7
            }
        },
        'matsuda_schedule': {
            'enabled': True,
            'index': 2,
            'pattern': 'biweekly',
            'reference_date': '2025-02-20'
        }
    }


@pytest.fixture
def sample_ng_dates():
    """テスト用NG日設定"""
    return {
        'ng_dates': {
            'global': ['2025-01-01', '2025-12-31'],
            'by_member': {
                '丸岡': ['2025-03-25', '2025-03-26'],
                '今井': ['2025-04-10']
            },
            'by_period': {
                '大関': [
                    {
                        'start': '2025-08-10',
                        'end': '2025-08-20',
                        'reason': '夏季休暇'
                    }
                ]
            }
        }
    }


@pytest.fixture
def checker(sample_settings, sample_ng_dates):
    """ConstraintCheckerインスタンス"""
    return ConstraintChecker(sample_settings, sample_ng_dates)


@pytest.fixture
def member_stats():
    """テスト用メンバー統計"""
    return {
        '丸岡': {
            'total_count': 10,
            'day_count': 6,
            'night_count': 4,
            'day_indexes': [1, 2],
            'night_indexes': [1],
            'last_date': date(2025, 3, 10),
            'first_date': date(2024, 11, 1)
        },
        '大関': {
            'total_count': 8,
            'day_count': 8,
            'night_count': 0,
            'day_indexes': [3],
            'night_indexes': [],
            'last_date': date(2025, 3, 12),
            'first_date': date(2024, 11, 5)
        },
        '松田': {
            'total_count': 12,
            'day_count': 0,
            'night_count': 12,
            'day_indexes': [],
            'night_indexes': [2],
            'last_date': date(2025, 3, 15),
            'first_date': date(2024, 10, 20)
        }
    }


# =============================================================================
# 日勤index制約テスト
# =============================================================================

def test_check_day_index_constraint_valid_1_2_to_1_2(checker, member_stats):
    """index 1,2経験者 → index 1,2配置可能"""
    ok, msg = checker.check_day_index_constraint('丸岡', 1, member_stats)
    assert ok is True
    assert msg == ""

    ok, msg = checker.check_day_index_constraint('丸岡', 2, member_stats)
    assert ok is True
    assert msg == ""


def test_check_day_index_constraint_invalid_1_2_to_3(checker, member_stats):
    """index 1,2経験者 → index 3配置不可"""
    ok, msg = checker.check_day_index_constraint('丸岡', 3, member_stats)
    assert ok is False
    assert 'index 3に配置不可' in msg


def test_check_day_index_constraint_valid_3_to_3(checker, member_stats):
    """index 3経験者 → index 3配置可能"""
    ok, msg = checker.check_day_index_constraint('大関', 3, member_stats)
    assert ok is True
    assert msg == ""


def test_check_day_index_constraint_invalid_3_to_1_2(checker, member_stats):
    """index 3経験者 → index 1,2配置不可"""
    ok, msg = checker.check_day_index_constraint('大関', 1, member_stats)
    assert ok is False
    assert 'index 1に配置不可' in msg

    ok, msg = checker.check_day_index_constraint('大関', 2, member_stats)
    assert ok is False
    assert 'index 2に配置不可' in msg


def test_check_day_index_constraint_new_member(checker, member_stats):
    """新メンバー（過去実績なし） → すべて配置可能"""
    ok, msg = checker.check_day_index_constraint('新人', 1, member_stats)
    assert ok is True

    ok, msg = checker.check_day_index_constraint('新人', 3, member_stats)
    assert ok is True


# =============================================================================
# 夜勤index制約テスト
# =============================================================================

def test_check_night_index_constraint_valid_1_to_1(checker, member_stats):
    """index 1経験者 → index 1配置可能"""
    ok, msg = checker.check_night_index_constraint('丸岡', 1, member_stats)
    assert ok is True
    assert msg == ""


def test_check_night_index_constraint_invalid_1_to_2(checker, member_stats):
    """index 1経験者 → index 2配置不可"""
    ok, msg = checker.check_night_index_constraint('丸岡', 2, member_stats)
    assert ok is False
    assert 'index 2に配置不可' in msg


def test_check_night_index_constraint_valid_2_to_2(checker, member_stats):
    """index 2経験者 → index 2配置可能"""
    ok, msg = checker.check_night_index_constraint('松田', 2, member_stats)
    assert ok is True
    assert msg == ""


def test_check_night_index_constraint_invalid_2_to_1(checker, member_stats):
    """index 2経験者 → index 1配置不可"""
    ok, msg = checker.check_night_index_constraint('松田', 1, member_stats)
    assert ok is False
    assert 'index 1に配置不可' in msg


# =============================================================================
# 重複禁止制約テスト
# =============================================================================

def test_check_overlap_constraint_no_conflict(checker):
    """重複なし → OK"""
    current_schedule = {
        'day': {
            date(2025, 3, 22): {1: '丸岡', 2: '今井', 3: '大関'}
        },
        'night': {
            date(2025, 3, 24): {1: '宮本', 2: '松田'}
        }
    }
    ok, msg = checker.check_overlap_constraint('丸岡', date(2025, 3, 22), current_schedule)
    assert ok is True


def test_check_overlap_constraint_day_and_night_same_week(checker):
    """同じ週に日勤と夜勤 → NG"""
    current_schedule = {
        'day': {
            date(2025, 3, 29): {1: '丸岡', 2: '今井', 3: '大関'}  # 土曜日（3/24週に含まれる）
        },
        'night': {
            date(2025, 3, 24): {1: '丸岡', 2: '松田'}  # 月曜～日曜（3/24～3/30）
        }
    }
    ok, msg = checker.check_overlap_constraint('丸岡', date(2025, 3, 29), current_schedule)
    assert ok is False
    assert '重複' in msg or '不可' in msg


# =============================================================================
# 夜勤→日勤ギャップ制約テスト
# =============================================================================

def test_check_night_to_day_gap_enough_days(checker, member_stats):
    """夜勤終了後8日経過 → OK（最小7日）"""
    current_schedule = {
        'night': {
            date(2025, 3, 10): {1: '丸岡', 2: '松田'}  # 3/10(月)～3/16(日)
        },
        'day': {}
    }
    target_date = date(2025, 3, 25)  # 3/16 + 9日
    ok, msg = checker.check_night_to_day_gap('丸岡', target_date, current_schedule, member_stats)
    assert ok is True


def test_check_night_to_day_gap_insufficient_days(checker, member_stats):
    """夜勤終了後3日 → NG（最小7日必要）"""
    current_schedule = {
        'night': {
            date(2025, 3, 10): {1: '丸岡', 2: '松田'}  # 3/10(月)～3/16(日)
        },
        'day': {}
    }
    target_date = date(2025, 3, 19)  # 3/16 + 3日
    ok, msg = checker.check_night_to_day_gap('丸岡', target_date, current_schedule, member_stats)
    assert ok is False
    assert '7日間は日勤不可' in msg


# =============================================================================
# 日勤最小間隔制約テスト
# =============================================================================

def test_check_min_interval_day_enough_days(checker, member_stats):
    """前回日勤から15日経過 → OK（最小14日）"""
    current_schedule = {
        'day': {
            date(2025, 3, 10): {1: '丸岡', 2: '今井', 3: '大関'}
        },
        'night': {}
    }
    target_date = date(2025, 3, 25)  # +15日
    ok, msg = checker.check_min_interval_day('丸岡', target_date, current_schedule, member_stats)
    assert ok is True


def test_check_min_interval_day_insufficient_days(checker, member_stats):
    """前回日勤から7日 → NG（最小14日必要）"""
    current_schedule = {
        'day': {
            date(2025, 3, 10): {1: '丸岡', 2: '今井', 3: '大関'}
        },
        'night': {}
    }
    target_date = date(2025, 3, 17)  # +7日
    ok, msg = checker.check_min_interval_day('丸岡', target_date, current_schedule, member_stats)
    assert ok is False
    assert '最小14日必要' in msg


# =============================================================================
# 夜勤最小間隔制約テスト
# =============================================================================

def test_check_min_interval_night_enough_days(checker, member_stats):
    """前回夜勤から22日経過 → OK（最小21日）"""
    current_schedule = {
        'night': {
            date(2025, 3, 3): {1: '丸岡', 2: '松田'}  # 3/3(月)～3/9(日)
        },
        'day': {}
    }
    target_week = date(2025, 3, 25)  # 3/3 + 22日
    ok, msg = checker.check_min_interval_night('丸岡', target_week, current_schedule, member_stats)
    assert ok is True


def test_check_min_interval_night_insufficient_days(checker, member_stats):
    """前回夜勤から14日 → NG（最小21日必要）"""
    current_schedule = {
        'night': {
            date(2025, 3, 3): {1: '丸岡', 2: '松田'}
        },
        'day': {}
    }
    target_week = date(2025, 3, 17)  # 3/3 + 14日
    ok, msg = checker.check_min_interval_night('丸岡', target_week, current_schedule, member_stats)
    assert ok is False
    assert '最小21日必要' in msg


# =============================================================================
# NG日制約テスト
# =============================================================================

def test_check_ng_dates_global(checker):
    """全体NG日 → NG"""
    target_date = date(2025, 1, 1)
    ok, msg = checker.check_ng_dates('丸岡', target_date)
    assert ok is False
    assert '全体NG日' in msg


def test_check_ng_dates_by_member(checker):
    """メンバー別NG日 → NG"""
    target_date = date(2025, 3, 25)
    ok, msg = checker.check_ng_dates('丸岡', target_date)
    assert ok is False
    assert 'NG日' in msg


def test_check_ng_dates_by_period(checker):
    """期間指定NG日 → NG"""
    target_date = date(2025, 8, 15)  # 8/10～8/20の期間内
    ok, msg = checker.check_ng_dates('大関', target_date)
    assert ok is False
    assert 'NG期間' in msg
    assert '夏季休暇' in msg


def test_check_ng_dates_ok(checker):
    """NG日に該当しない → OK"""
    target_date = date(2025, 3, 30)
    ok, msg = checker.check_ng_dates('今井', target_date)
    assert ok is True
    assert msg == ""


# =============================================================================
# 松田さん隔週パターンテスト
# =============================================================================

def test_check_matsuda_biweekly_even_week(checker):
    """基準日から偶数週 → True（松田さん配置）"""
    reference_date = date(2025, 2, 20)  # 木曜日（基準）
    target_week = date(2025, 3, 6)  # 2週後の月曜日（偶数週）
    is_matsuda_week = checker.check_matsuda_biweekly(target_week, reference_date)
    assert is_matsuda_week is True


def test_check_matsuda_biweekly_odd_week(checker):
    """基準日から奇数週 → False（松田さん配置しない）"""
    reference_date = date(2025, 2, 20)
    target_week = date(2025, 2, 27)  # 1週後の月曜日（奇数週）
    is_matsuda_week = checker.check_matsuda_biweekly(target_week, reference_date)
    assert is_matsuda_week is False


# =============================================================================
# 統合制約チェックテスト
# =============================================================================

def test_validate_all_constraints_all_ok(checker, member_stats):
    """すべての制約OK → True, []"""
    current_schedule = {
        'day': {},
        'night': {}
    }
    ok, errors = checker.validate_all_constraints(
        member='丸岡',
        target_date=date(2025, 4, 5),
        shift_type='day',
        target_index=1,
        current_schedule=current_schedule,
        member_stats=member_stats
    )
    assert ok is True
    assert len(errors) == 0


def test_validate_all_constraints_multiple_violations(checker, member_stats):
    """複数の制約違反 → False, [エラーリスト]"""
    current_schedule = {
        'day': {
            date(2025, 3, 22): {1: '丸岡', 2: '今井', 3: '大関'}
        },
        'night': {}
    }
    # 丸岡をindex 3に配置（index制約違反）、かつ前回日勤から7日（間隔制約違反）
    ok, errors = checker.validate_all_constraints(
        member='丸岡',
        target_date=date(2025, 3, 29),  # 3/22 + 7日
        shift_type='day',
        target_index=3,
        current_schedule=current_schedule,
        member_stats=member_stats
    )
    assert ok is False
    assert len(errors) >= 2  # index制約 + 間隔制約
