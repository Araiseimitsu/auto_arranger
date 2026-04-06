"""履歴CSVの追記処理。"""

import shutil
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from src.output_formatter import OutputFormatter


def append_generated_schedule_to_history(
    schedule: Dict,
    csv_path: Path | str,
) -> Dict[str, Any]:
    """生成したスケジュールを履歴CSVへ追記する。"""
    target_path = Path(csv_path)
    formatter = OutputFormatter()
    new_rows = formatter.schedule_to_dataframe(schedule)

    if new_rows.empty:
        raise ValueError("保存対象のスケジュールが空です")

    target_path.parent.mkdir(parents=True, exist_ok=True)

    required_columns = ['date', 'shift_category', 'shift_index', 'person_name']
    added_count = len(new_rows)
    skipped_count = 0

    if target_path.exists():
        existing_df = pd.read_csv(target_path)
        missing_columns = [column for column in required_columns if column not in existing_df.columns]
        if missing_columns:
            missing = ', '.join(missing_columns)
            raise ValueError(f"履歴CSVに必要な列がありません: {missing}")

        existing_keys = {
            (
                str(row.date),
                str(row.shift_category),
                int(row.shift_index),
                str(row.person_name),
            )
            for row in existing_df[required_columns].itertuples(index=False)
        }
        new_keys = [
            (row.date, row.shift_category, int(row.shift_index), row.person_name)
            for row in new_rows.itertuples(index=False)
        ]
        append_mask = [key not in existing_keys for key in new_keys]
        rows_to_append = new_rows.loc[append_mask].copy()
        added_count = len(rows_to_append)
        skipped_count = len(new_rows) - added_count

        if rows_to_append.empty:
            return {
                'path': str(target_path),
                'added_count': 0,
                'skipped_count': skipped_count,
            }

        shutil.copy(target_path, target_path.with_suffix('.bak'))
        rows_to_append.to_csv(
            target_path,
            mode='a',
            header=False,
            index=False,
            encoding='utf-8'
        )
    else:
        new_rows.to_csv(target_path, index=False, encoding='utf-8-sig')

    return {
        'path': str(target_path),
        'added_count': added_count,
        'skipped_count': skipped_count,
    }