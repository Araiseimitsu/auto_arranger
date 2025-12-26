"""
設定ファイル自動生成モジュール
"""
import yaml
from pathlib import Path
from typing import Dict, List
import pandas as pd
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ConfigGenerator:
    """設定ファイル自動生成クラス"""

    def __init__(self, output_dir: str = "config"):
        """
        初期化

        Args:
            output_dir: 出力ディレクトリ
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_settings_from_history(
        self,
        member_stats: Dict,
        matsuda_last_date: str = "auto"
    ) -> Dict:
        """
        過去データからsettings.yamlの内容を生成

        Args:
            member_stats: メンバー統計情報（data_loader.analyze_member_historyの戻り値）
            matsuda_last_date: 松田さんの最終担当日（"auto"で自動計算）

        Returns:
            設定辞書
        """
        logger.info("settings.yaml自動生成開始")

        # メンバーをindex所属ごとに分類
        day_index_1_2_group = []
        day_index_3_group = []
        night_index_1_group = []
        night_index_2_group = []

        for member, stats in member_stats.items():
            # 日勤分類
            if stats['day_count'] > 0:
                day_indexes = stats['day_indexes']
                if 3 in day_indexes:
                    # index 3に出現したことがある → index_3_group
                    day_index_3_group.append({'name': member, 'active': True})
                elif 1 in day_indexes or 2 in day_indexes:
                    # index 1または2に出現 → index_1_2_group
                    day_index_1_2_group.append({'name': member, 'active': True})

            # 夜勤分類
            if stats['night_count'] > 0:
                night_indexes = stats['night_indexes']
                if 2 in night_indexes:
                    # index 2に出現したことがある → index_2_group
                    member_config = {'name': member, 'active': True}
                    # 松田さんの場合は固定パターンを追加
                    if member == '松田':
                        member_config['fixed_pattern'] = 'biweekly'
                    night_index_2_group.append(member_config)
                elif 1 in night_indexes:
                    # index 1に出現 → index_1_group
                    night_index_1_group.append({'name': member, 'active': True})

        # 松田さんの基準日を自動計算
        reference_date = matsuda_last_date
        if matsuda_last_date == "auto" and '松田' in member_stats:
            reference_date = member_stats['松田']['last_date'].isoformat()
            logger.info(f"松田さんの基準日を自動検出: {reference_date}")

        # 設定辞書を構築
        config = {
            'members': {
                'day_shift': {
                    'index_1_2_group': sorted(day_index_1_2_group, key=lambda x: x['name']),
                    'index_3_group': sorted(day_index_3_group, key=lambda x: x['name'])
                },
                'night_shift': {
                    'index_1_group': sorted(night_index_1_group, key=lambda x: x['name']),
                    'index_2_group': sorted(night_index_2_group, key=lambda x: x['name'])
                }
            },
            'matsuda_schedule': {
                'enabled': True,
                'index': 2,
                'pattern': 'biweekly',
                'reference_date': reference_date
            },
            'constraints': {
                'rotation_period': {
                    'start_day': 21,
                    'duration_months': 2
                },
                'fairness': {
                    'max_deviation_ratio': 0.3
                },
                'interval': {
                    'min_days_between_same_person_day': 14,
                    'min_days_between_same_person_night': 21,
                    'min_days_between_same_person_day_index3': 7
                },
                'no_overlap': {
                    'enabled': True
                },
                'night_to_day_gap': {
                    'min_days': 7
                },
                'soft_constraints': {
                    'day_to_night_gap': {
                        'enabled': True,
                        'days_threshold_strong': 3,
                        'days_threshold_weak': 7,
                        'penalty_strong': 0.3,
                        'penalty_weak': 0.15
                    }
                }
            },
            'historical_data': {
                'lookback_months': 2,
                'csv_path': 'data/duty_roster_2021_2025.csv'
            },
            'output': {
                'format': 'table',
                'show_statistics': True,
                'save_to_file': True,
                'output_dir': 'data/output'
            }
        }

        logger.info(f"メンバー分類完了:")
        logger.info(f"  日勤 index 1,2: {len(day_index_1_2_group)}名")
        logger.info(f"  日勤 index 3: {len(day_index_3_group)}名")
        logger.info(f"  夜勤 index 1: {len(night_index_1_group)}名")
        logger.info(f"  夜勤 index 2: {len(night_index_2_group)}名")

        return config

    def save_settings(self, config: Dict, filename: str = "settings.yaml") -> None:
        """
        設定をYAMLファイルに保存

        Args:
            config: 設定辞書
            filename: ファイル名
        """
        filepath = self.output_dir / filename
        logger.info(f"設定ファイル保存: {filepath}")

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        logger.info("保存完了")

    def generate_ng_dates_template(self, filename: str = "ng_dates.yaml") -> None:
        """
        NG日設定ファイルの雛形を生成

        Args:
            filename: ファイル名
        """
        filepath = self.output_dir / filename

        if filepath.exists():
            logger.info(f"NG日設定ファイルは既に存在します: {filepath}")
            return

        logger.info(f"NG日設定ファイル雛形作成: {filepath}")

        template = {
            'ng_dates': {
                'by_member': {
                    '例_メンバー名': [
                        '2025-03-15',
                        '2025-03-16'
                    ]
                },
                'global': [
                    '2025-01-01'  # 元日（例）
                ],
                'by_period': {
                    '例_メンバー名': [
                        {
                            'start': '2025-08-10',
                            'end': '2025-08-20',
                            'reason': '夏季休暇'
                        }
                    ]
                }
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(template, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        logger.info("雛形作成完了")


def auto_generate_config(member_stats: Dict, output_dir: str = "config") -> None:
    """
    過去データから設定ファイルを自動生成

    Args:
        member_stats: メンバー統計情報
        output_dir: 出力ディレクトリ
    """
    generator = ConfigGenerator(output_dir)

    # settings.yaml生成
    config = generator.generate_settings_from_history(member_stats)
    generator.save_settings(config)

    # ng_dates.yaml雛形生成
    generator.generate_ng_dates_template()

    logger.info("設定ファイル自動生成完了")
