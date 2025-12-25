"""
当番表自動作成システム - メインエントリーポイント

使用例:
    py -3.13 main.py --start 2025-03-21
    py -3.13 main.py --start 2025-03-21 --debug
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from utils.logger import setup_logger
from utils.date_utils import get_rotation_period
from src.data_loader import load_and_process_data
from src.schedule_builder import ScheduleBuilder
from src.output_formatter import OutputFormatter


def main():
    """メイン処理"""
    # コマンドライン引数パース
    parser = argparse.ArgumentParser(
        description='当番表自動作成システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  py -3.13 main.py --start 2025-03-21
  py -3.13 main.py --start 2025-03-21 --debug
  py -3.13 main.py --start 2025-03-21 --output schedule.csv
        """
    )

    parser.add_argument(
        '--start',
        type=str,
        required=True,
        help='ローテーション開始日（YYYY-MM-DD形式、月の21日を推奨）'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='デバッグモード（詳細ログ出力）'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='CSV出力ファイルパス（オプション）'
    )

    args = parser.parse_args()

    # ロガー設定
    log_level = 'DEBUG' if args.debug else 'INFO'
    logger = setup_logger('main', log_level)

    try:
        # 開始日のパース
        start_date = date.fromisoformat(args.start)
        logger.info(f"開始日: {start_date}")

        # 2ヶ月後の20日を終了日として計算
        _, end_date = get_rotation_period(start_date)
        logger.info(f"終了日: {end_date}")

        # 設定ファイルパス
        settings_path = 'config/settings.yaml'
        ng_dates_path = 'config/ng_dates.yaml'
        csv_path = 'data/duty_roster_2021_2025.csv'

        # ファイル存在確認
        for path in [settings_path, ng_dates_path, csv_path]:
            if not Path(path).exists():
                logger.error(f"ファイルが見つかりません: {path}")
                sys.exit(1)

        logger.info("設定ファイル読み込み中...")

        # 過去データ読み込み
        logger.info("過去データ読み込み中...")
        df_all, df_recent, member_stats = load_and_process_data(
            csv_path,
            lookback_months=2
        )

        logger.info(f"過去データ: {len(df_all)}行")
        logger.info(f"直近2ヶ月データ: {len(df_recent)}行")
        logger.info(f"アクティブメンバー: {len(member_stats)}名")

        # スケジュール構築
        logger.info("スケジュール構築中...")
        builder = ScheduleBuilder(
            settings_path,
            ng_dates_path,
            member_stats,
            df_recent
        )

        schedule = builder.build_schedule(start_date, end_date)

        logger.info("スケジュール構築完了")

        # 出力
        formatter = OutputFormatter()

        # 統計情報生成
        statistics = formatter.generate_statistics(schedule, member_stats)

        # 標準出力に表示
        print(f"\n{'='*80}")
        print(f"当番表自動作成システム")
        print(f"期間: {start_date} ～ {end_date}")
        print(f"{'='*80}")

        formatter.print_schedule(schedule, start_date, end_date, statistics)

        # CSV出力（オプション）
        if args.output:
            formatter.save_to_csv(schedule, args.output)
            logger.info(f"スケジュールをCSVに保存: {args.output}")

        logger.info("処理が正常に完了しました")
        sys.exit(0)

    except ValueError as e:
        # 制約違反エラー
        logger.error(f"制約違反により処理を中断しました")
        logger.error(str(e))
        sys.exit(1)

    except Exception as e:
        # その他のエラー
        logger.error(f"予期しないエラーが発生しました: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
