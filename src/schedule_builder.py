"""
スケジュール構築モジュール

グリーディアルゴリズムでスケジュールを段階的に構築します。
優先度スコアに基づいて最適な候補者を選定します。
"""

import yaml
from datetime import date, timedelta
from typing import Dict, List, Tuple, Any, Optional
from utils.logger import setup_logger
from utils.date_utils import get_weekends_in_period, get_mondays_in_period
from src.constraint_checker import ConstraintChecker


logger = setup_logger(__name__, 'INFO')


class ScheduleBuilder:
    """
    スケジュール構築クラス
    """

    def __init__(
        self,
        settings_path: str,
        ng_dates_path: str,
        member_stats: Dict,
        recent_df=None
    ):
        """
        初期化

        Args:
            settings_path: settings.yamlのパス
            ng_dates_path: ng_dates.yamlのパス
            member_stats: メンバー統計情報
            recent_df: 直近データのDataFrame（オプション）
        """
        # 設定読み込み
        with open(settings_path, 'r', encoding='utf-8') as f:
            self.settings = yaml.safe_load(f)

        with open(ng_dates_path, 'r', encoding='utf-8') as f:
            self.ng_dates_config = yaml.safe_load(f)

        self.member_stats = member_stats
        self.recent_df = recent_df

        # 制約チェッカー初期化
        self.checker = ConstraintChecker(self.settings, self.ng_dates_config)

        # メンバーグループ取得
        members = self.settings.get('members', {})
        day_shift = members.get('day_shift', {})
        night_shift = members.get('night_shift', {})

        self.day_index_1_2_group = [
            m['name'] for m in day_shift.get('index_1_2_group', [])
            if m.get('active', True)
        ]
        self.day_index_3_group = [
            m['name'] for m in day_shift.get('index_3_group', [])
            if m.get('active', True)
        ]
        self.night_index_1_group = [
            m['name'] for m in night_shift.get('index_1_group', [])
            if m.get('active', True)
        ]
        self.night_index_2_group = [
            m['name'] for m in night_shift.get('index_2_group', [])
            if m.get('active', True)
        ]

        # 松田さんの設定
        self.matsuda_config = self.settings.get('matsuda_schedule', {})
        self.matsuda_enabled = self.matsuda_config.get('enabled', False)
        if self.matsuda_enabled:
            self.matsuda_reference_date = date.fromisoformat(
                self.matsuda_config.get('reference_date', '2025-02-20')
            )

        logger.info(f"スケジュール構築初期化完了")
        logger.info(f"日勤 index 1,2: {len(self.day_index_1_2_group)}名")
        logger.info(f"日勤 index 3: {len(self.day_index_3_group)}名")
        logger.info(f"夜勤 index 1: {len(self.night_index_1_group)}名")
        logger.info(f"夜勤 index 2: {len(self.night_index_2_group)}名")

    def build_schedule(
        self,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        スケジュールを構築

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            スケジュール辞書
        """
        logger.info(f"スケジュール構築開始: {start_date} ～ {end_date}")

        schedule = {
            'day': {},
            'night': {}
        }

        # 夜勤スケジュール生成（先に実行）
        self._assign_night_shifts(schedule, start_date, end_date)

        # 日勤スケジュール生成
        self._assign_day_shifts(schedule, start_date, end_date)

        logger.info(f"スケジュール構築完了")
        return schedule

    def _assign_day_shifts(
        self,
        schedule: Dict,
        start_date: date,
        end_date: date
    ) -> None:
        """
        日勤スケジュールを割り当て

        Args:
            schedule: スケジュール辞書（更新される）
            start_date: 開始日
            end_date: 終了日
        """
        weekends = get_weekends_in_period(start_date, end_date)
        logger.info(f"日勤対象日数: {len(weekends)}日")

        # Global NG日（会社休日）を取得
        global_ng_dates = set()
        ng_dates = self.ng_dates_config.get('ng_dates', {})
        if ng_dates:
            global_ng_list = ng_dates.get('global', [])
            if global_ng_list:
                for d_str in global_ng_list:
                    try:
                        global_ng_dates.add(date.fromisoformat(d_str))
                    except ValueError:
                        pass

        for weekend_date in weekends:
            # 会社休日（Global NG）の場合はスキップ
            if weekend_date in global_ng_dates:
                logger.info(f"会社休日（Global NG）のため、{weekend_date}の日勤割り当てをスキップします")
                continue

            schedule['day'][weekend_date] = {}

            # Index 1, 2, 3 を順番に割り当て
            for index in [1, 2, 3]:
                # 候補者グループを取得
                if index in [1, 2]:
                    candidates = self.day_index_1_2_group.copy()
                else:
                    candidates = self.day_index_3_group.copy()

                # 最適な候補を選択
                selected = self._select_best_candidate(
                    candidates,
                    weekend_date,
                    'day',
                    index,
                    schedule
                )

                if selected is None:
                    # 候補が見つからない場合
                    self._raise_no_candidate_error(
                        weekend_date, 'day', index, candidates, schedule
                    )

                schedule['day'][weekend_date][index] = selected
                logger.debug(f"日勤: {weekend_date} Index {index} → {selected}")

    def _assign_night_shifts(
        self,
        schedule: Dict,
        start_date: date,
        end_date: date
    ) -> None:
        """
        夜勤スケジュールを割り当て

        Args:
            schedule: スケジュール辞書（更新される）
            start_date: 開始日
            end_date: 終了日
        """
        mondays = get_mondays_in_period(start_date, end_date)
        logger.info(f"夜勤対象週数: {len(mondays)}週")

        # Global NG日（会社休日）を取得
        global_ng_dates = set()
        ng_dates = self.ng_dates_config.get('ng_dates', {})
        if ng_dates:
            global_ng_list = ng_dates.get('global', [])
            if global_ng_list:
                for d_str in global_ng_list:
                    try:
                        global_ng_dates.add(date.fromisoformat(d_str))
                    except ValueError:
                        pass

        for monday in mondays:
            # 週の平日（月～金）がすべてGlobal NGかチェック
            is_full_holiday_week = True
            for i in range(5):  # 0(Mon) to 4(Fri)
                check_date = monday + timedelta(days=i)
                if check_date not in global_ng_dates:
                    is_full_holiday_week = False
                    break
            
            if is_full_holiday_week:
                logger.info(f"平日全休（Global NG）のため、{monday}週の夜勤割り当てをスキップします")
                continue

            schedule['night'][monday] = {}

            # Index 1 を割り当て
            candidates = self.night_index_1_group.copy()
            selected = self._select_best_candidate(
                candidates,
                monday,
                'night',
                1,
                schedule
            )

            if selected is None:
                self._raise_no_candidate_error(
                    monday, 'night', 1, candidates, schedule
                )

            schedule['night'][monday][1] = selected
            logger.debug(f"夜勤: {monday} Index 1 → {selected}")

            # Index 2 を割り当て（松田さん優先）
            if self.matsuda_enabled and self.checker.check_matsuda_biweekly(monday, self.matsuda_reference_date):
                # 松田さんの週
                matsuda_name = '松田'
                # 制約チェック
                ok, errors = self.checker.validate_all_constraints(
                    matsuda_name, monday, 'night', 2, schedule, self.member_stats
                )
                if ok:
                    schedule['night'][monday][2] = matsuda_name
                    logger.debug(f"夜勤: {monday} Index 2 → {matsuda_name} (固定)")
                else:
                    logger.warning(f"松田さんを{monday}に配置できません: {errors}")
                    # 他の候補を探す
                    candidates = [m for m in self.night_index_2_group if m != matsuda_name]
                    selected = self._select_best_candidate(
                        candidates, monday, 'night', 2, schedule
                    )
                    if selected is None:
                        self._raise_no_candidate_error(
                            monday, 'night', 2, candidates, schedule
                        )
                    schedule['night'][monday][2] = selected
                    logger.debug(f"夜勤: {monday} Index 2 → {selected} (松田さん代替)")
            else:
                # 松田さん以外の週
                candidates = self.night_index_2_group.copy()
                selected = self._select_best_candidate(
                    candidates, monday, 'night', 2, schedule
                )
                if selected is None:
                    self._raise_no_candidate_error(
                        monday, 'night', 2, candidates, schedule
                    )
                schedule['night'][monday][2] = selected
                logger.debug(f"夜勤: {monday} Index 2 → {selected}")

    def _select_best_candidate(
        self,
        candidates: List[str],
        target_date: date,
        shift_type: str,
        index: int,
        current_schedule: Dict
    ) -> Optional[str]:
        """
        最適な候補者を選択

        Args:
            candidates: 候補者リスト
            target_date: 配置予定日
            shift_type: 'day' or 'night'
            index: index番号
            current_schedule: 現在のスケジュール

        Returns:
            選択されたメンバー名（候補がいない場合はNone）
        """
        valid_candidates = []

        for candidate in candidates:
            # 制約チェック
            ok, errors = self.checker.validate_all_constraints(
                candidate, target_date, shift_type, index,
                current_schedule, self.member_stats
            )

            if ok:
                # 優先度スコア計算
                score = self._calculate_priority_score(
                    candidate, shift_type, current_schedule
                )
                valid_candidates.append((candidate, score))
                logger.debug(f"  候補: {candidate} (スコア: {score:.3f})")
            else:
                logger.debug(f"  候補: {candidate} → 制約違反: {errors[0] if errors else '不明'}")

        if not valid_candidates:
            return None

        # スコアが最も高い候補を選択
        valid_candidates.sort(key=lambda x: x[1], reverse=True)
        selected = valid_candidates[0][0]

        return selected

    def _calculate_priority_score(
        self,
        member: str,
        shift_type: str,
        current_schedule: Dict
    ) -> float:
        """
        優先度スコアを計算

        要素:
        1. 現在スケジュールでの担当回数の少なさ（重み: 0.5）
        2. 最終担当からの経過日数（重み: 0.3）
        3. 過去の担当頻度の低さ（重み: 0.2）

        Args:
            member: メンバー名
            shift_type: 'day' or 'night'
            current_schedule: 現在のスケジュール

        Returns:
            優先度スコア（高いほど優先）
        """
        score = 0.0

        # 1. 現在スケジュールでの担当回数（少ないほど高スコア）
        current_count = self._count_in_schedule(member, shift_type, current_schedule)
        score += (1.0 / (current_count + 1)) * 0.5

        # 2. 最終担当からの経過日数（長いほど高スコア）
        last_date = self._get_last_assignment(member, shift_type, current_schedule)
        if last_date:
            days_since = (date.today() - last_date).days
            score += min(days_since / 30.0, 1.0) * 0.3
        else:
            score += 1.0 * 0.3  # 未担当は最大スコア

        # 3. 過去の担当頻度（少ないほど高スコア）
        if member in self.member_stats:
            past_count = self.member_stats[member].get(f'{shift_type}_count', 0)
            score += (1.0 / (past_count + 1)) * 0.2
        else:
            score += 1.0 * 0.2

        return score

    def _count_in_schedule(
        self,
        member: str,
        shift_type: str,
        current_schedule: Dict
    ) -> int:
        """
        現在のスケジュールでの担当回数をカウント

        Args:
            member: メンバー名
            shift_type: 'day' or 'night'
            current_schedule: 現在のスケジュール

        Returns:
            担当回数
        """
        count = 0
        schedule = current_schedule.get(shift_type, {})

        for date_or_week, indexes in schedule.items():
            for idx, assigned_member in indexes.items():
                if assigned_member == member:
                    count += 1

        return count

    def _get_last_assignment(
        self,
        member: str,
        shift_type: str,
        current_schedule: Dict
    ) -> Optional[date]:
        """
        最終担当日を取得

        Args:
            member: メンバー名
            shift_type: 'day' or 'night'
            current_schedule: 現在のスケジュール

        Returns:
            最終担当日（担当がない場合はNone）
        """
        schedule = current_schedule.get(shift_type, {})
        last_date = None

        for date_or_week, indexes in sorted(schedule.items(), reverse=True):
            for idx, assigned_member in indexes.items():
                if assigned_member == member:
                    last_date = date_or_week
                    break
            if last_date:
                break

        # 過去データからも確認
        if last_date is None and member in self.member_stats:
            last_date = self.member_stats[member].get('last_date')

        return last_date

    def _raise_no_candidate_error(
        self,
        target_date: date,
        shift_type: str,
        index: int,
        candidates: List[str],
        current_schedule: Dict
    ) -> None:
        """
        候補者がいない場合のエラーを発生

        Args:
            target_date: 配置予定日
            shift_type: 'day' or 'night'
            index: index番号
            candidates: 候補者リスト
            current_schedule: 現在のスケジュール
        """
        shift_name = "日勤" if shift_type == 'day' else "夜勤"
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        weekday = weekday_names[target_date.weekday()]

        error_msg = f"\nエラー: {target_date}（{weekday}）{shift_name} Index {index} に割り当て可能な候補者がいません。\n"
        error_msg += f"\n【制約チェック結果】\n"

        for candidate in candidates[:5]:  # 上位5名のみ表示
            error_msg += f"\n候補者: {candidate}\n"

            # 各制約をチェック
            ok, errors = self.checker.validate_all_constraints(
                candidate, target_date, shift_type, index,
                current_schedule, self.member_stats
            )

            if ok:
                error_msg += f"  ✓ すべての制約OK\n"
            else:
                for error in errors:
                    error_msg += f"  ✗ {error}\n"

        error_msg += f"\n【推奨対応】\n"
        error_msg += f"1. NG日設定を確認してください（config/ng_dates.yaml）\n"
        error_msg += f"2. メンバーのアクティブ状態を確認してください（config/settings.yaml）\n"
        error_msg += f"3. 制約パラメータの緩和を検討してください\n"

        logger.error(error_msg)
        raise ValueError(error_msg)
