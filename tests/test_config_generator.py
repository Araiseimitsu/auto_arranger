"""
config_generator.pyのテスト
"""
import pytest
import yaml
from pathlib import Path
from src.config_generator import ConfigGenerator, auto_generate_config
from src.data_loader import load_and_process_data


class TestConfigGenerator:
    """設定ファイル生成のテスト"""

    @pytest.fixture
    def generator(self, tmp_path):
        """テスト用ジェネレーターインスタンス（一時ディレクトリ使用）"""
        return ConfigGenerator(output_dir=str(tmp_path))

    @pytest.fixture
    def member_stats(self):
        """テスト用メンバー統計データ"""
        _, _, stats = load_and_process_data(
            "data/duty_roster_2021_2025.csv",
            lookback_months=2
        )
        return stats

    def test_generate_settings_from_history(self, generator, member_stats):
        """過去データからの設定生成テスト"""
        config = generator.generate_settings_from_history(member_stats)

        # 設定の構造が正しいこと
        assert 'members' in config
        assert 'day_shift' in config['members']
        assert 'night_shift' in config['members']
        assert 'matsuda_schedule' in config
        assert 'constraints' in config
        assert 'historical_data' in config
        assert 'output' in config

        # 日勤メンバーグループが存在すること
        assert 'index_1_2_group' in config['members']['day_shift']
        assert 'index_3_group' in config['members']['day_shift']

        # 夜勤メンバーグループが存在すること
        assert 'index_1_group' in config['members']['night_shift']
        assert 'index_2_group' in config['members']['night_shift']

        # メンバーが分類されていること
        day_12_count = len(config['members']['day_shift']['index_1_2_group'])
        day_3_count = len(config['members']['day_shift']['index_3_group'])
        night_1_count = len(config['members']['night_shift']['index_1_group'])
        night_2_count = len(config['members']['night_shift']['index_2_group'])

        assert day_12_count > 0
        assert day_3_count > 0
        assert night_1_count > 0
        assert night_2_count > 0

    def test_matsuda_schedule_in_config(self, generator, member_stats):
        """松田さんのスケジュール設定テスト"""
        config = generator.generate_settings_from_history(member_stats)

        # 松田さんの設定が含まれていること
        matsuda_config = config['matsuda_schedule']
        assert matsuda_config['enabled'] == True
        assert matsuda_config['index'] == 2
        assert matsuda_config['pattern'] == 'biweekly'
        # 基準日が設定されていること
        assert 'reference_date' in matsuda_config

        # 松田さんが夜勤index2グループに含まれていること
        night_index_2_members = config['members']['night_shift']['index_2_group']
        matsuda_found = False
        for member in night_index_2_members:
            if member['name'] == '松田':
                matsuda_found = True
                assert member.get('fixed_pattern') == 'biweekly'
                break
        assert matsuda_found, "松田さんが夜勤index2グループに見つかりません"

    def test_save_settings(self, generator, member_stats, tmp_path):
        """設定ファイル保存のテスト"""
        config = generator.generate_settings_from_history(member_stats)
        generator.save_settings(config, filename="test_settings.yaml")

        # ファイルが作成されていること
        filepath = tmp_path / "test_settings.yaml"
        assert filepath.exists()

        # ファイルが読み込めること
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded_config = yaml.safe_load(f)

        # 内容が一致すること
        assert loaded_config == config

    def test_generate_ng_dates_template(self, generator, tmp_path):
        """NG日設定テンプレート生成のテスト"""
        generator.generate_ng_dates_template(filename="test_ng_dates.yaml")

        # ファイルが作成されていること
        filepath = tmp_path / "test_ng_dates.yaml"
        assert filepath.exists()

        # ファイルが読み込めること
        with open(filepath, 'r', encoding='utf-8') as f:
            ng_config = yaml.safe_load(f)

        # 必要な構造が含まれていること
        assert 'ng_dates' in ng_config
        assert 'by_member' in ng_config['ng_dates']
        assert 'global' in ng_config['ng_dates']
        assert 'by_period' in ng_config['ng_dates']

    def test_member_classification(self, generator, member_stats):
        """メンバー分類の正確性テスト"""
        config = generator.generate_settings_from_history(member_stats)

        # 日勤index1,2グループのメンバーは日勤でindex1または2に出現しているはず
        for member_info in config['members']['day_shift']['index_1_2_group']:
            member_name = member_info['name']
            if member_name in member_stats:
                stats = member_stats[member_name]
                # 日勤に出現している場合、index1または2のはず
                if stats['day_count'] > 0:
                    assert 1 in stats['day_indexes'] or 2 in stats['day_indexes']

        # 日勤index3グループのメンバーは日勤でindex3に出現しているはず
        for member_info in config['members']['day_shift']['index_3_group']:
            member_name = member_info['name']
            if member_name in member_stats:
                stats = member_stats[member_name]
                # 日勤に出現している場合、index3のはず
                if stats['day_count'] > 0:
                    assert 3 in stats['day_indexes']

        # 夜勤index2グループのメンバーは夜勤でindex2に出現しているはず
        for member_info in config['members']['night_shift']['index_2_group']:
            member_name = member_info['name']
            if member_name in member_stats:
                stats = member_stats[member_name]
                # 夜勤に出現している場合、index2のはず
                if stats['night_count'] > 0:
                    assert 2 in stats['night_indexes']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
