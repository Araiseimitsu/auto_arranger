"""
CSVデータ読み込み・前処理モジュール
"""
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DutyRosterLoader:
    """当番データローダー"""

    def __init__(self, csv_path: str):
        """
        初期化

        Args:
            csv_path: CSVファイルのパス
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

    def load_csv(self) -> pd.DataFrame:
        """
        CSVファイルを読み込む

        Returns:
            読み込んだDataFrame
        """
        logger.info(f"CSVファイル読み込み開始: {self.csv_path}")
        df = pd.DataFrame()
        try:
            df = pd.read_csv(self.csv_path)
            logger.info(f"読み込み完了: {len(df)}行")
            return df
        except Exception as e:
            logger.error(f"CSVファイル読み込みエラー: {e}")
            raise

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        データクリーニング

        - 重複行を除去
        - 欠損値・変更マーカーを除外
        - 日付をdatetime型に変換

        Args:
            df: 元のDataFrame

        Returns:
            クリーニング済みのDataFrame
        """
        logger.info("データクリーニング開始")
        original_len = len(df)

        # 重複行を除去
        df = df.drop_duplicates()
        duplicate_removed = original_len - len(df)
        logger.info(f"重複行除去: {duplicate_removed}行")

        # 無効なデータを除外（"-", "変更→", "person_name"など）
        invalid_names = ['-', '変更→', 'person_name']
        df = df[~df['person_name'].isin(invalid_names)]
        invalid_removed = original_len - duplicate_removed - len(df)
        logger.info(f"無効データ除去: {invalid_removed}行")

        # 日付をdatetime型に変換
        df['date'] = pd.to_datetime(df['date'])

        # shift_indexを整数型に変換
        df['shift_index'] = df['shift_index'].astype(int)

        logger.info(f"クリーニング完了: {len(df)}行")
        return df

    def get_recent_data(self, df: pd.DataFrame, months: int, reference_date: date = None) -> pd.DataFrame:
        """
        直近N ヶ月のデータを抽出

        Args:
            df: DataFrame
            months: 抽出する月数
            reference_date: 基準日（Noneの場合は最新日）

        Returns:
            抽出されたDataFrame
        """
        if reference_date is None:
            reference_date = df['date'].max().date()

        start_date = reference_date - timedelta(days=months * 30)  # 概算
        logger.info(f"直近{months}ヶ月のデータ抽出: {start_date} ～ {reference_date}")

        recent_df = df[df['date'] >= pd.Timestamp(start_date)].copy()
        logger.info(f"抽出完了: {len(recent_df)}行")

        return recent_df

    def analyze_member_history(self, df: pd.DataFrame) -> Dict:
        """
        メンバーの履歴を分析

        Args:
            df: DataFrame

        Returns:
            メンバーごとの統計情報
        """
        logger.info("メンバー履歴分析開始")

        stats = {}
        for member in df['person_name'].unique():
            member_data = df[df['person_name'] == member]

            # 日勤・夜勤の回数とindex
            day_data = member_data[member_data['shift_category'] == 'Day']
            night_data = member_data[member_data['shift_category'] == 'Night']

            stats[member] = {
                'total_count': len(member_data),
                'day_count': len(day_data),
                'night_count': len(night_data),
                'day_indexes': sorted(day_data['shift_index'].unique().tolist()) if len(day_data) > 0 else [],
                'night_indexes': sorted(night_data['shift_index'].unique().tolist()) if len(night_data) > 0 else [],
                'last_date': member_data['date'].max().date(),
                'first_date': member_data['date'].min().date()
            }

        logger.info(f"分析完了: {len(stats)}名")
        return stats

    def get_active_members(self, df: pd.DataFrame, months: int = 2) -> List[str]:
        """
        アクティブなメンバーを取得（直近N ヶ月に出現したメンバー）

        Args:
            df: DataFrame
            months: 判定する月数

        Returns:
            アクティブメンバーのリスト
        """
        recent_df = self.get_recent_data(df, months)
        active_members = sorted(recent_df['person_name'].unique().tolist())
        logger.info(f"アクティブメンバー: {len(active_members)}名")
        return active_members


def load_and_process_data(csv_path: str, lookback_months: int = 2) -> tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    データの読み込みと処理を一括で実行

    Args:
        csv_path: CSVファイルのパス
        lookback_months: 過去何ヶ月分を参照するか

    Returns:
        (全データ, 直近データ, メンバー統計) のタプル
    """
    loader = DutyRosterLoader(csv_path)

    # CSVロード
    df_all = loader.load_csv()

    # クリーニング
    df_all = loader.clean_data(df_all)

    # 直近データ抽出
    df_recent = loader.get_recent_data(df_all, lookback_months)

    # メンバー履歴分析
    member_stats = loader.analyze_member_history(df_recent)

    return df_all, df_recent, member_stats
