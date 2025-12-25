"""
出力フォーマッターモジュール

スケジュールをテーブル形式で表示し、統計情報レポートを生成します。
"""

import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Any
from tabulate import tabulate


class OutputFormatter:
    """
    スケジュール出力フォーマッタークラス
    """

    def __init__(self):
        """初期化"""
        pass

    def format_schedule_table(
        self,
        schedule: Dict,
        start_date: date,
        end_date: date
    ) -> str:
        """
        スケジュールをテーブル形式でフォーマット

        Args:
            schedule: スケジュール辞書
            start_date: 開始日
            end_date: 終了日

        Returns:
            テーブル形式の文字列
        """
        output = []

        # 日勤スケジュールテーブル
        output.append("\n【日勤スケジュール】")
        day_table = self._format_day_schedule_table(schedule.get('day', {}))
        output.append(day_table)

        # 夜勤スケジュールテーブル
        output.append("\n【夜勤スケジュール】")
        night_table = self._format_night_schedule_table(schedule.get('night', {}))
        output.append(night_table)

        return "\n".join(output)

    def _format_day_schedule_table(self, day_schedule: Dict) -> str:
        """
        日勤スケジュールをテーブル形式でフォーマット

        Args:
            day_schedule: 日勤スケジュール辞書

        Returns:
            テーブル文字列
        """
        if not day_schedule:
            return "（なし）"

        weekday_names = ['月', '火', '水', '木', '金', '土', '日']

        # テーブルデータ作成
        table_data = []
        for day_date in sorted(day_schedule.keys()):
            indexes = day_schedule[day_date]
            weekday = weekday_names[day_date.weekday()]

            row = [
                str(day_date),
                weekday,
                indexes.get(1, '-'),
                indexes.get(2, '-'),
                indexes.get(3, '-')
            ]
            table_data.append(row)

        headers = ['日付', '曜日', 'Index 1', 'Index 2', 'Index 3']

        return tabulate(table_data, headers=headers, tablefmt='simple')

    def _format_night_schedule_table(self, night_schedule: Dict) -> str:
        """
        夜勤スケジュールをテーブル形式でフォーマット

        Args:
            night_schedule: 夜勤スケジュール辞書

        Returns:
            テーブル文字列
        """
        if not night_schedule:
            return "（なし）"

        # テーブルデータ作成
        table_data = []
        for week_start in sorted(night_schedule.keys()):
            indexes = night_schedule[week_start]
            week_end = week_start + timedelta(days=6)
            period_str = f"{week_start.month:02d}/{week_start.day:02d} - {week_end.month:02d}/{week_end.day:02d}"

            row = [
                str(week_start),
                period_str,
                indexes.get(1, '-'),
                indexes.get(2, '-')
            ]
            table_data.append(row)

        headers = ['週（月曜開始）', '期間', 'Index 1', 'Index 2']

        return tabulate(table_data, headers=headers, tablefmt='simple')

    def generate_statistics(
        self,
        schedule: Dict,
        member_stats: Dict = None
    ) -> Dict:
        """
        統計情報を生成

        Args:
            schedule: スケジュール辞書
            member_stats: メンバー統計情報（オプション）

        Returns:
            統計情報辞書
        """
        stats = {}

        # メンバー別担当回数を集計
        member_counts = {}

        # 日勤カウント
        day_schedule = schedule.get('day', {})
        for day_date, indexes in day_schedule.items():
            for idx, member in indexes.items():
                if member not in member_counts:
                    member_counts[member] = {'day': 0, 'night': 0}
                member_counts[member]['day'] += 1

        # 夜勤カウント
        night_schedule = schedule.get('night', {})
        for week_start, indexes in night_schedule.items():
            for idx, member in indexes.items():
                if member not in member_counts:
                    member_counts[member] = {'day': 0, 'night': 0}
                member_counts[member]['night'] += 1

        stats['member_counts'] = member_counts

        # 総担当回数の計算
        total_counts = {
            member: counts['day'] + counts['night']
            for member, counts in member_counts.items()
        }

        stats['total_counts'] = total_counts

        # 公平性指標の計算
        if total_counts:
            max_count = max(total_counts.values())
            min_count = min(total_counts.values())
            avg_count = sum(total_counts.values()) / len(total_counts)

            if min_count > 0:
                fairness_ratio = (max_count - min_count) / min_count
            else:
                fairness_ratio = float('inf')

            stats['fairness'] = {
                'max_count': max_count,
                'min_count': min_count,
                'avg_count': avg_count,
                'deviation_ratio': fairness_ratio
            }

        return stats

    def print_statistics_report(
        self,
        statistics: Dict,
        target_ratio: float = 0.3
    ) -> str:
        """
        統計情報レポートを生成

        Args:
            statistics: 統計情報
            target_ratio: 目標偏差比（デフォルト0.3）

        Returns:
            レポート文字列
        """
        output = []

        output.append("\n【統計情報】")

        # メンバー別担当回数テーブル
        member_counts = statistics.get('member_counts', {})

        if member_counts:
            table_data = []
            for member in sorted(member_counts.keys()):
                counts = member_counts[member]
                total = counts['day'] + counts['night']
                row = [member, counts['day'], counts['night'], total]
                table_data.append(row)

            headers = ['メンバー', '日勤', '夜勤', '合計']
            output.append(tabulate(table_data, headers=headers, tablefmt='simple'))

        # 公平性指標
        fairness = statistics.get('fairness', {})
        if fairness:
            output.append(f"\n公平性指標:")
            output.append(f"  最大担当回数: {fairness['max_count']}回")
            output.append(f"  最小担当回数: {fairness['min_count']}回")
            output.append(f"  平均担当回数: {fairness['avg_count']:.2f}回")

            deviation_ratio = fairness['deviation_ratio']
            if deviation_ratio == float('inf'):
                output.append(f"  偏差比: 計算不可（最小回数が0）")
            else:
                status = "✓" if deviation_ratio <= target_ratio else "✗"
                output.append(f"  偏差比: {deviation_ratio:.2f} (基準: {target_ratio}以内) {status}")

        return "\n".join(output)

    def save_to_csv(
        self,
        schedule: Dict,
        output_path: str
    ) -> None:
        """
        スケジュールをCSVファイルに保存

        Args:
            schedule: スケジュール辞書
            output_path: 出力ファイルパス
        """
        records = []

        # 日勤レコード
        day_schedule = schedule.get('day', {})
        for day_date, indexes in day_schedule.items():
            for idx, member in indexes.items():
                records.append({
                    'date': day_date,
                    'shift_category': 'Day',
                    'shift_index': idx,
                    'person_name': member
                })

        # 夜勤レコード
        night_schedule = schedule.get('night', {})
        for week_start, indexes in night_schedule.items():
            for idx, member in indexes.items():
                records.append({
                    'date': week_start,
                    'shift_category': 'Night',
                    'shift_index': idx,
                    'person_name': member
                })

        # DataFrameに変換
        df = pd.DataFrame(records)

        # 日付でソート
        df = df.sort_values('date')

        # CSV保存
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

    def print_schedule(
        self,
        schedule: Dict,
        start_date: date,
        end_date: date,
        statistics: Dict = None
    ) -> None:
        """
        スケジュールと統計情報を標準出力に表示

        Args:
            schedule: スケジュール辞書
            start_date: 開始日
            end_date: 終了日
            statistics: 統計情報（オプション）
        """
        # スケジュールテーブル
        schedule_table = self.format_schedule_table(schedule, start_date, end_date)
        print(schedule_table)

        # 統計情報
        if statistics:
            stats_report = self.print_statistics_report(statistics)
            print(stats_report)
