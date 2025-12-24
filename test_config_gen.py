"""
設定ファイル自動生成のテストスクリプト
"""
from src.data_loader import load_and_process_data
from src.config_generator import auto_generate_config
from utils.logger import setup_logger

logger = setup_logger(__name__, level="INFO")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("設定ファイル自動生成テスト開始")
    logger.info("=" * 60)

    # データ読み込みと処理
    csv_path = "data/duty_roster_2021_2025.csv"
    logger.info(f"CSVファイル: {csv_path}")

    df_all, df_recent, member_stats = load_and_process_data(csv_path, lookback_months=2)

    logger.info(f"\n全データ: {len(df_all)}行")
    logger.info(f"直近2ヶ月: {len(df_recent)}行")
    logger.info(f"アクティブメンバー: {len(member_stats)}名\n")

    # メンバー統計の表示（上位10名）
    logger.info("メンバー統計（上位10名）:")
    sorted_members = sorted(member_stats.items(), key=lambda x: x[1]['total_count'], reverse=True)[:10]
    for member, stats in sorted_members:
        logger.info(f"  {member}: 計{stats['total_count']}回 (日勤{stats['day_count']}, 夜勤{stats['night_count']})")
        logger.info(f"    日勤index: {stats['day_indexes']}, 夜勤index: {stats['night_indexes']}")

    # 設定ファイル自動生成
    logger.info("\n" + "=" * 60)
    auto_generate_config(member_stats, output_dir="config")
    logger.info("=" * 60)

    logger.info("\n✓ テスト完了")
    logger.info("config/settings.yaml と config/ng_dates.yaml を確認してください")


if __name__ == "__main__":
    main()
