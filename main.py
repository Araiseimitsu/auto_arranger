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
    parser.add_argument(
        '--variants',
        type=int,
        default=1,
        help='同一条件で別バージョンを生成する数（デフォルト: 1）'
    )
    parser.add_argument(
        '--variant-top-k',
        type=int,
        default=3,
        help='各枠で上位k候補から選ぶ幅（バリアント用、デフォルト: 3）'
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
        formatter = OutputFormatter()
        variant_count = max(1, int(args.variants))
        variant_top_k = max(1, int(args.variant_top_k))
        schedules = []
        failures = []

        for variant_index in range(variant_count):
            builder = ScheduleBuilder(
                settings_path,
                ng_dates_path,
                member_stats,
                df_recent,
                variant_index=variant_index,
                variant_top_k=variant_top_k
            )
            try:
                schedule = builder.build_schedule(start_date, end_date)
                schedules.append((variant_index, schedule))
            except ValueError as e:
                failures.append((variant_index, str(e)))
                if variant_count == 1:
                    raise

        if not schedules:
            logger.error("すべてのバリアントでスケジュール生成に失敗しました")
            for variant_index, message in failures:
                logger.error(f"バージョン{variant_index + 1}失敗: {message}")
            sys.exit(1)

        logger.info("スケジュール構築完了")

        # 標準出力に表示
        print(f"\n{'='*80}")
        print(f"当番表自動作成システム")
        print(f"期間: {start_date} ～ {end_date}")
        print(f"{'='*80}")

        for variant_index, schedule in schedules:
            statistics = formatter.generate_statistics(schedule, member_stats)
            if variant_count > 1:
                print(f"\n--- バージョン{variant_index + 1}/{variant_count} ---")
            formatter.print_schedule(schedule, start_date, end_date, statistics)

            # CSV出力（オプション）
            if args.output:
                output_path = args.output
                if variant_count > 1:
                    path = Path(args.output)
                    suffix = path.suffix if path.suffix else ".csv"
                    stem = path.stem if path.stem else "schedule"
                    output_path = str(path.with_name(f"{stem}_v{variant_index + 1}{suffix}"))
                formatter.save_to_csv(schedule, output_path)
                logger.info(f"スケジュールをCSVに保存: {output_path}")

        if failures:
            for variant_index, message in failures:
                logger.warning(f"バージョン{variant_index + 1}は生成失敗: {message}")

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
