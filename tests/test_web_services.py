from datetime import date
from io import BytesIO

import pandas as pd

from src.history_csv import append_generated_schedule_to_history
from web.services import import_history_csv_files, save_history_csv_page


def build_sample_schedule():
    return {
        'day': {
            date(2026, 4, 11): {1: '山田', 2: '佐藤', 3: '鈴木'},
        },
        'night': {
            date(2026, 4, 6): {1: '高橋', 2: '田中'},
        },
    }


def test_append_generated_schedule_to_history_creates_new_csv(tmp_path):
    csv_path = tmp_path / 'history.csv'

    result = append_generated_schedule_to_history(build_sample_schedule(), csv_path=csv_path)

    df = pd.read_csv(csv_path)

    assert result['path'] == str(csv_path)
    assert result['added_count'] == 5
    assert result['skipped_count'] == 0
    assert len(df) == 5
    assert list(df.columns) == ['date', 'shift_category', 'shift_index', 'person_name']


def test_append_generated_schedule_to_history_skips_existing_rows(tmp_path):
    csv_path = tmp_path / 'history.csv'
    schedule = build_sample_schedule()

    first_result = append_generated_schedule_to_history(schedule, csv_path=csv_path)
    second_result = append_generated_schedule_to_history(schedule, csv_path=csv_path)
    df = pd.read_csv(csv_path)

    assert first_result['added_count'] == 5
    assert second_result['added_count'] == 0
    assert second_result['skipped_count'] == 5
    assert len(df) == 5


def test_append_generated_schedule_to_history_creates_backup_when_appending(tmp_path):
    csv_path = tmp_path / 'history.csv'

    append_generated_schedule_to_history(build_sample_schedule(), csv_path=csv_path)

    additional_schedule = {
        'day': {
            date(2026, 4, 12): {1: '伊藤', 2: '渡辺', 3: '中村'},
        },
        'night': {},
    }

    result = append_generated_schedule_to_history(additional_schedule, csv_path=csv_path)
    df = pd.read_csv(csv_path)

    assert result['added_count'] == 3
    assert result['skipped_count'] == 0
    assert len(df) == 8
    assert csv_path.with_suffix('.bak').exists()


def test_save_history_csv_page_edits_slice(tmp_path):
    csv_path = tmp_path / 'history_edit.csv'
    append_generated_schedule_to_history(build_sample_schedule(), csv_path=csv_path)
    df_sorted = pd.read_csv(csv_path).sort_values('date', ascending=False).reset_index(drop=True)
    r0 = df_sorted.iloc[0]
    r1 = df_sorted.iloc[1]
    d0 = pd.Timestamp(r0['date']).strftime('%Y-%m-%d')
    d1 = pd.Timestamp(r1['date']).strftime('%Y-%m-%d')
    rows = [
        {
            'date': d0,
            'shift_category': str(r0['shift_category']),
            'shift_index': int(r0['shift_index']),
            'person_name': 'PATCH_A',
        },
        {
            'date': d1,
            'shift_category': str(r1['shift_category']),
            'shift_index': int(r1['shift_index']),
            'person_name': 'PATCH_B',
        },
    ]
    ok, msg = save_history_csv_page(1, 2, rows, csv_path=csv_path)
    assert ok
    assert '保存' in msg
    df2 = pd.read_csv(csv_path).sort_values('date', ascending=False).reset_index(drop=True)
    assert df2.iloc[0]['person_name'] == 'PATCH_A'
    assert df2.iloc[1]['person_name'] == 'PATCH_B'
    assert csv_path.with_suffix('.bak').exists()


def test_save_history_csv_page_rejects_night_index_three(tmp_path):
    csv_path = tmp_path / 'history_bad.csv'
    append_generated_schedule_to_history(build_sample_schedule(), csv_path=csv_path)
    df_sorted = pd.read_csv(csv_path).sort_values('date', ascending=False).reset_index(drop=True)
    r0 = df_sorted.iloc[0]
    d0 = pd.Timestamp(r0['date']).strftime('%Y-%m-%d')
    rows = [
        {
            'date': d0,
            'shift_category': 'Night',
            'shift_index': 3,
            'person_name': 'X',
        },
    ]
    ok, msg = save_history_csv_page(1, 1, rows, csv_path=csv_path)
    assert not ok
    assert '夜勤' in msg


def test_import_history_csv_files_merges_multiple_files_and_deduplicates(tmp_path):
    csv_path = tmp_path / 'history_import.csv'

    file_a = type(
        'UploadStub',
        (),
        {
            'filename': 'a.csv',
            'file': BytesIO(
                (
                    'date,shift_category,shift_index,person_name\n'
                    '2026-04-20,Day,1,A\n'
                    '2026-04-19,Night,1,B\n'
                ).encode('utf-8')
            ),
        },
    )()
    file_b = type(
        'UploadStub',
        (),
        {
            'filename': 'nested/b.csv',
            'file': BytesIO(
                (
                    'date,shift_category,shift_index,person_name\n'
                    '2026-04-20,Day,1,A\n'
                    '2026-04-18,Day,2,C\n'
                ).encode('utf-8')
            ),
        },
    )()

    result = import_history_csv_files([file_a, file_b], csv_path=csv_path)
    df = pd.read_csv(csv_path)

    assert result['file_count'] == 2
    assert result['row_count'] == 3
    assert len(df) == 3
    assert list(df['person_name']) == ['A', 'B', 'C']
