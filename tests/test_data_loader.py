"""
data_loader.pyのテスト
"""
import pytest
import pandas as pd
from datetime import date
from src.data_loader import DutyRosterLoader, load_and_process_data


class TestDataLoader:
    """データローダーのテスト"""

    @pytest.fixture
    def loader(self):
        """テスト用ローダーインスタンス"""
        return DutyRosterLoader("data/duty_roster_2021_2025.csv")

    def test_load_csv(self, loader):
        """CSV読み込みのテスト"""
        df = loader.load_csv()

        # データが読み込まれていること
        assert len(df) > 0
        # 必要なカラムが存在すること
        assert 'date' in df.columns
        assert 'shift_category' in df.columns
        assert 'shift_index' in df.columns
        assert 'person_name' in df.columns

    def test_clean_data(self, loader):
        """データクリーニングのテスト"""
        df_raw = loader.load_csv()
        original_len = len(df_raw)

        df_clean = loader.clean_data(df_raw)

        # 重複が除去されていること
        assert len(df_clean) < original_len
        # 無効なデータが除去されていること
        assert '-' not in df_clean['person_name'].values
        assert '変更→' not in df_clean['person_name'].values
        assert 'person_name' not in df_clean['person_name'].values
        # 日付がdatetime型に変換されていること
        assert pd.api.types.is_datetime64_any_dtype(df_clean['date'])
        # shift_indexが整数型であること
        assert pd.api.types.is_integer_dtype(df_clean['shift_index'])

    def test_get_recent_data(self, loader):
        """直近データ抽出のテスト"""
        df = loader.load_csv()
        df = loader.clean_data(df)

        # 直近2ヶ月のデータを抽出
        df_recent = loader.get_recent_data(df, months=2)

        # データが抽出されていること
        assert len(df_recent) > 0
        # 全データより少ないこと
        assert len(df_recent) < len(df)

    def test_analyze_member_history(self, loader):
        """メンバー履歴分析のテスト"""
        df = loader.load_csv()
        df = loader.clean_data(df)
        df_recent = loader.get_recent_data(df, months=2)

        stats = loader.analyze_member_history(df_recent)

        # 統計情報が生成されていること
        assert len(stats) > 0

        # 各メンバーに必要な情報が含まれていること
        for member, info in stats.items():
            assert 'total_count' in info
            assert 'day_count' in info
            assert 'night_count' in info
            assert 'day_indexes' in info
            assert 'night_indexes' in info
            assert 'last_date' in info
            assert 'first_date' in info

        # 松田さんの情報をチェック
        if '松田' in stats:
            matsuda_stats = stats['松田']
            # 夜勤が多いこと
            assert matsuda_stats['night_count'] > 0
            # 夜勤index2に出現していること
            assert 2 in matsuda_stats['night_indexes']

    def test_get_active_members(self, loader):
        """アクティブメンバー取得のテスト"""
        df = loader.load_csv()
        df = loader.clean_data(df)

        active_members = loader.get_active_members(df, months=2)

        # アクティブメンバーが存在すること
        assert len(active_members) > 0
        # リストがソートされていること
        assert active_members == sorted(active_members)

    def test_load_and_process_data(self):
        """統合処理のテスト"""
        df_all, df_recent, member_stats = load_and_process_data(
            "data/duty_roster_2021_2025.csv",
            lookback_months=2
        )

        # 全データが読み込まれていること
        assert len(df_all) > 0
        # 直近データが抽出されていること
        assert len(df_recent) > 0
        assert len(df_recent) < len(df_all)
        # メンバー統計が生成されていること
        assert len(member_stats) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
