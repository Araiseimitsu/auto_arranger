"""
ログ設定モジュール
"""
import logging
import sys
from pathlib import Path


def setup_logger(name: str = "auto_arranger", level: str = "INFO", log_file: str = None) -> logging.Logger:
    """
    ロガーをセットアップする

    Args:
        name: ロガー名
        level: ログレベル（DEBUG, INFO, WARNING, ERROR）
        log_file: ログファイルパス（Noneの場合はコンソールのみ）

    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 既存のハンドラーをクリア
    logger.handlers.clear()

    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラー（指定された場合）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# デフォルトロガー
logger = setup_logger()
