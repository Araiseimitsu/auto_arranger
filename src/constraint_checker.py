"""
制約チェッカーモジュール

当番スケジュールの8つの制約条件をチェックします。
各制約関数は (制約OK: bool, エラーメッセージ: str) のタプルを返します。
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple, Any


class ConstraintChecker:
    """
    スケジュール制約をチェックするクラス
    """

    def __init__(self, settings: Dict, ng_dates_config: Dict):
        """
        初期化

        Args:
            settings: settings.yamlの内容
            ng_dates_config: ng_dates.yamlの内容
        """
        self.settings = settings
        self.ng_dates_config = ng_dates_config

        # 制約パラメータを取得
        constraints = settings.get('constraints', {})
        self.min_days_day = constraints.get('interval', {}).get('min_days_between_same_person_day', 14)
        self.min_days_night = constraints.get('interval', {}).get('min_days_between_same_person_night', 21)
        self.min_days_day_index3 = constraints.get('interval', {}).get('min_days_between_same_person_day_index3', 7)
        self.night_to_day_gap = constraints.get('night_to_day_gap', {}).get('min_days', 7)

        # メンバー個別設定のマップを作成
        self.member_configs = {}
        if 'members' in settings:
            m = settings['members']
            # Helper to extract configs
            def extract_configs(group_list):
                if not group_list: return
                for member in group_list:
                    # 既存の設定があればマージ（後勝ち、または最初の設定を優先）
                    # ここでは単純に上書きしますが、通常同じメンバーの設定は同期されている前提
                    if member['name'] not in self.member_configs:
                        self.member_configs[member['name']] = member
                    else:
                        # 既存の設定に属性を追加（例: interval設定が片方にしかない場合など）
                        self.member_configs[member['name']].update(member)

            if 'day_shift' in m:
                extract_configs(m['day_shift'].get('index_1_2_group', []))
                extract_configs(m['day_shift'].get('index_3_group', []))
            if 'night_shift' in m:
                extract_configs(m['night_shift'].get('index_1_group', []))
                extract_configs(m['night_shift'].get('index_2_group', []))

    def _get_member_min_days_day(self, member: str) -> int:
        """メンバーごとの日勤最小間隔を取得（設定がなければデフォルト）"""
        if member in self.member_configs:
             val = self.member_configs[member].get('min_days_day')
             if val is not None: return int(val)
        return self.min_days_day

    def _get_member_min_days_night(self, member: str) -> int:
        """メンバーごとの夜勤最小間隔を取得（設定がなければデフォルト）"""
        if member in self.member_configs:
             val = self.member_configs[member].get('min_days_night')
             if val is not None: return int(val)
        return self.min_days_night

    def check_day_index_constraint(
        self,
        member: str,
        target_index: int,
        member_stats: Dict
    ) -> Tuple[bool, str]:
        """
        日勤のindex制約をチェック

        ルール:
        - 過去2ヶ月でindex 1,2経験 → index 3配置不可
        - 過去2ヶ月でindex 3経験 → index 1,2配置不可

        Args:
            member: メンバー名
            target_index: 配置予定のindex (1, 2, 3)
            member_stats: メンバー統計情報

        Returns:
            (制約OK, エラーメッセージ)
        """
        if member not in member_stats:
            return True, ""

        past_indexes = member_stats[member].get('day_indexes', [])

        # index 1,2経験者がindex 3に配置される場合
        if target_index == 3 and any(i in [1, 2] for i in past_indexes):
            return False, f"{member}は過去にindex 1,2を経験しているため、index 3に配置不可"

        # index 3経験者がindex 1,2に配置される場合
        if target_index in [1, 2] and 3 in past_indexes:
            return False, f"{member}は過去にindex 3を経験しているため、index {target_index}に配置不可"

        return True, ""

    def check_night_index_constraint(
        self,
        member: str,
        target_index: int,
        member_stats: Dict
    ) -> Tuple[bool, str]:
        """
        夜勤のindex制約をチェック

        ルール:
        - 過去2ヶ月でindex 1経験 → index 2配置不可
        - 過去2ヶ月でindex 2経験 → index 1配置不可

        Args:
            member: メンバー名
            target_index: 配置予定のindex (1, 2)
            member_stats: メンバー統計情報

        Returns:
            (制約OK, エラーメッセージ)
        """
        if member not in member_stats:
            return True, ""

        past_indexes = member_stats[member].get('night_indexes', [])

        # index 1経験者がindex 2に配置される場合
        if target_index == 2 and 1 in past_indexes:
            return False, f"{member}は過去にindex 1を経験しているため、index 2に配置不可"

        # index 2経験者がindex 1に配置される場合
        if target_index == 1 and 2 in past_indexes:
            return False, f"{member}は過去にindex 2を経験しているため、index 1に配置不可"

        return True, ""

    def check_overlap_constraint(
        self,
        member: str,
        target_date: date,
        shift_type: str,
        current_schedule: Dict
    ) -> Tuple[bool, str]:
        """
        日勤・夜勤重複禁止制約をチェック

        ルール:
        - 同じ日に日勤と夜勤に同時配置不可
        - 今回割り当てようとしている日時と、既存スケジュールの重複のみをチェック

        Args:
            member: メンバー名
            target_date: 配置予定日（土日の日勤日 or 月曜開始の夜勤週）
            shift_type: 'day' または 'night'
            current_schedule: 現在のスケジュール

        Returns:
            (制約OK, エラーメッセージ)
        """
        day_schedule = current_schedule.get('day', {})
        night_schedule = current_schedule.get('night', {})

        if shift_type == 'day':
            # ケース1: 日勤を配置しようとしている
            # -> その日が、既存の夜勤週（期間）に含まれていないかチェック
            for week_start, night_indexes in night_schedule.items():
                week_end = week_start + timedelta(days=6)
                
                # ターゲット日が夜勤期間に含まれる場合
                if week_start <= target_date <= week_end:
                    # その夜勤週に本人がアサインされているか確認
                    for night_idx, night_member in night_indexes.items():
                        if night_member == member:
                            return False, f"{member}は{week_start}～{week_end}に夜勤配置済み、{target_date}に日勤は不可"

        elif shift_type == 'night':
            # ケース2: 夜勤を配置しようとしている
            # -> その週（期間）の中に、既に日勤が入っていないかチェック
            week_start = target_date
            week_end = week_start + timedelta(days=6)

            for day_date, day_indexes in day_schedule.items():
                # 日勤日が今回の夜勤期間に含まれる場合
                if week_start <= day_date <= week_end:
                    # その日勤日に本人がアサインされているか確認
                    for day_idx, day_member in day_indexes.items():
                        if day_member == member:
                            return False, f"{member}は{day_date}に日勤配置済み、{week_start}～{week_end}に夜勤は不可"

        return True, ""

    def check_night_to_day_gap(
        self,
        member: str,
        target_date: date,
        current_schedule: Dict,
        member_stats: Dict = None
    ) -> Tuple[bool, str]:
        """
        夜勤→日勤ギャップ制約をチェック

        ルール:
        - 夜勤終了後7日間は日勤配置不可

        Args:
            member: メンバー名
            target_date: 配置予定の日勤日
            current_schedule: 現在のスケジュール
            member_stats: メンバー統計情報（過去データ参照用、オプション）

        Returns:
            (制約OK, エラーメッセージ)
        """
        night_schedule = current_schedule.get('night', {})

        for week_start, indexes in night_schedule.items():
            for idx, assigned_member in indexes.items():
                if assigned_member == member:
                    # 夜勤終了日（日曜日）
                    night_end = week_start + timedelta(days=6)
                    days_since = (target_date - night_end).days

                    if 0 < days_since < self.night_to_day_gap:
                        return False, f"{member}は{night_end}に夜勤終了、{self.night_to_day_gap}日間は日勤不可（あと{self.night_to_day_gap - days_since}日必要）"

        # 過去データからもチェック（オプション）
        if member_stats and member in member_stats:
            last_night_date = member_stats[member].get('last_date')
            if last_night_date and member_stats[member].get('night_count', 0) > 0:
                # 最終夜勤が週の開始日と仮定（簡易実装）
                # より厳密には夜勤の終了日を追跡する必要があります
                pass

        return True, ""

    def check_min_interval_day(
        self,
        member: str,
        target_date: date,
        target_index: int,
        current_schedule: Dict,
        member_stats: Dict
    ) -> Tuple[bool, str]:
        """
        日勤最小間隔制約をチェック

        ルール:
        - 同一メンバーの日勤間隔は最小n日以上
        - index 3は代休があるため7日、それ以外は設定値（通常14日）

        Args:
            member: メンバー名
            target_date: 配置予定日
            target_index: 配置予定のindex
            current_schedule: 現在のスケジュール
            member_stats: メンバー統計情報

        Returns:
            (制約OK, エラーメッセージ)
        """
        day_schedule = current_schedule.get('day', {})

        # index 3は代休があるため制約を緩和、それ以外は設定値(個別設定優先)
        min_days = self.min_days_day_index3 if target_index == 3 else self._get_member_min_days_day(member)

        # 現在のスケジュールから最終日勤日を取得
        last_day_date = None
        for day_date, indexes in sorted(day_schedule.items(), reverse=True):
            for idx, assigned_member in indexes.items():
                if assigned_member == member:
                    last_day_date = day_date
                    break
            if last_day_date:
                break

        if last_day_date:
            days_since = (target_date - last_day_date).days
            if days_since < min_days:
                return False, f"{member}は前回日勤({last_day_date})から{days_since}日、最小{min_days}日必要（あと{min_days - days_since}日必要）"

        return True, ""

    def check_min_interval_night(
        self,
        member: str,
        target_week_start: date,
        current_schedule: Dict,
        member_stats: Dict
    ) -> Tuple[bool, str]:
        """
        夜勤最小間隔制約をチェック

        ルール:
        - 同一メンバーの夜勤間隔は最小21日以上

        Args:
            member: メンバー名
            target_week_start: 配置予定の週の月曜日
            current_schedule: 現在のスケジュール
            member_stats: メンバー統計情報

        Returns:
            (制約OK, エラーメッセージ)
        """
        night_schedule = current_schedule.get('night', {})
        
        # 個別設定優先
        min_days = self._get_member_min_days_night(member)

        # 現在のスケジュールから最終夜勤週を取得
        last_night_week = None
        for week_start, indexes in sorted(night_schedule.items(), reverse=True):
            for idx, assigned_member in indexes.items():
                if assigned_member == member:
                    last_night_week = week_start
                    break
            if last_night_week:
                break

        if last_night_week:
            days_since = (target_week_start - last_night_week).days
            if days_since < min_days:
                return False, f"{member}は前回夜勤({last_night_week})から{days_since}日、最小{min_days}日必要（あと{min_days - days_since}日必要）"

        return True, ""

    def check_ng_dates(
        self,
        member: str,
        target_date: date
    ) -> Tuple[bool, str]:
        """
        NG日制約をチェック

        チェック項目:
        1. by_member: メンバー別NG日
        2. global: 全体NG日
        3. by_period: 期間指定NG日

        Args:
            member: メンバー名
            target_date: 配置予定日

        Returns:
            (制約OK, エラーメッセージ)
        """
        ng_dates = self.ng_dates_config.get('ng_dates', {})

        # グローバルNG日はスケジュール構築側で枠自体の有無として判定するため、
        # ここでは個人のNGチェックのみ行います。

        # メンバー別NG日
        by_member = ng_dates.get('by_member', {})
        member_ng_dates = by_member.get(member, [])
        for ng_date_str in member_ng_dates:
            if target_date == date.fromisoformat(ng_date_str):
                return False, f"{member}は{target_date}がNG日"

        # 期間指定NG日
        by_period = ng_dates.get('by_period', {})
        member_periods = by_period.get(member, [])
        for period in member_periods:
            start = date.fromisoformat(period['start'])
            end = date.fromisoformat(period['end'])
            if start <= target_date <= end:
                reason = period.get('reason', '期間NG')
                return False, f"{member}は{target_date}がNG期間({reason})"

        return True, ""

    def check_matsuda_biweekly(
        self,
        target_week_start: date,
        reference_date: date = None
    ) -> bool:
        """
        松田さんの隔週パターンをチェック

        ルール:
        - 松田さんは夜勤index 2に隔週で配置
        - 基準日から偶数週に配置

        Args:
            target_week_start: 配置予定の週の月曜日
            reference_date: 基準日（settings.yamlから取得、Noneの場合は自動取得）

        Returns:
            松田さんを配置すべき週かどうか
        """
        if reference_date is None:
            matsuda_config = self.settings.get('matsuda_schedule', {})
            ref_str = matsuda_config.get('reference_date')
            if ref_str:
                reference_date = date.fromisoformat(ref_str)
            else:
                # デフォルト基準日
                reference_date = date(2025, 2, 20)

        # 基準日からの週数を計算
        weeks_diff = (target_week_start - reference_date).days // 7

        # 偶数週に配置
        return weeks_diff % 2 == 0

    def validate_all_constraints(
        self,
        member: str,
        target_date: date,
        shift_type: str,  # 'day' or 'night'
        target_index: int,
        current_schedule: Dict,
        member_stats: Dict
    ) -> Tuple[bool, List[str]]:
        """
        すべての制約を一括チェック

        Args:
            member: メンバー名
            target_date: 配置予定日（日勤の場合）または週開始日（夜勤の場合）
            shift_type: 'day' または 'night'
            target_index: 配置予定のindex
            current_schedule: 現在のスケジュール
            member_stats: メンバー統計情報

        Returns:
            (すべての制約OK, エラーメッセージリスト)
        """
        errors = []

        # 1. Index制約
        if shift_type == 'day':
            ok, msg = self.check_day_index_constraint(member, target_index, member_stats)
            if not ok:
                errors.append(msg)
        else:
            ok, msg = self.check_night_index_constraint(member, target_index, member_stats)
            if not ok:
                errors.append(msg)

        # 2. 重複禁止
        ok, msg = self.check_overlap_constraint(member, target_date, shift_type, current_schedule)
        if not ok:
            errors.append(msg)

        # 3. 夜勤→日勤ギャップ（日勤配置時のみ）
        if shift_type == 'day':
            ok, msg = self.check_night_to_day_gap(member, target_date, current_schedule, member_stats)
            if not ok:
                errors.append(msg)

        # 4. 最小間隔
        if shift_type == 'day':
            ok, msg = self.check_min_interval_day(member, target_date, target_index, current_schedule, member_stats)
            if not ok:
                errors.append(msg)
        else:
            ok, msg = self.check_min_interval_night(member, target_date, current_schedule, member_stats)
            if not ok:
                errors.append(msg)

        # 5. NG日
        ok, msg = self.check_ng_dates(member, target_date)
        if not ok:
            errors.append(msg)

        return len(errors) == 0, errors
