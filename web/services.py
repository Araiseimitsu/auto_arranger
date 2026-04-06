import json
import yaml
import shutil
import sys
import math
from pathlib import Path
from datetime import date
from typing import Dict, Any, List, Tuple, Union, Optional

import pandas as pd
from src.data_loader import load_and_process_data, DutyRosterLoader
from src.history_csv import append_generated_schedule_to_history
from src.schedule_builder import ScheduleBuilder
from src.schedule_analyzer import ScheduleAnalyzer
from src.output_formatter import OutputFormatter
from src.ng_text_parser import parse_ng_text
from src.ng_status_view import build_ng_status_for_schedule
from utils.date_utils import get_rotation_period
from utils.logger import setup_logger

logger = setup_logger('web_services')

def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(relative_path)

def ensure_file_exists(local_path: Path, resource_path_str: str) -> None:
    """Ensure file exists locally, copying from bundle if necessary"""
    if not local_path.exists():
        bundled = get_resource_path(resource_path_str)
        if bundled.exists() and bundled != local_path:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy(bundled, local_path)
                logger.info(f"Copied default {resource_path_str} to {local_path}")
            except Exception as e:
                logger.error(f"Failed to copy default file: {e}")

# Define paths relative to CWD (where the user runs the exe)
SETTINGS_PATH = Path('config/settings.yaml')
NG_DATES_PATH = Path('config/ng_dates.yaml')
CSV_PATH = Path('data/duty_roster_2021_2025.csv')
OUTPUT_DIR = Path('data/output')

# Ensure configs exist on module load (or first access)
ensure_file_exists(SETTINGS_PATH, 'config/settings.yaml')
ensure_file_exists(NG_DATES_PATH, 'config/ng_dates.yaml')

def load_settings() -> Dict[str, Any]:
    ensure_file_exists(SETTINGS_PATH, 'config/settings.yaml')
    if not SETTINGS_PATH.exists():
        return {}
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_settings(data: Dict[str, Any]) -> None:
    # Backup before saving
    if SETTINGS_PATH.exists():
        shutil.copy(SETTINGS_PATH, SETTINGS_PATH.with_suffix('.yaml.bak'))
    else:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)

def load_ng_dates() -> Dict[str, Any]:
    ensure_file_exists(NG_DATES_PATH, 'config/ng_dates.yaml')
    if not NG_DATES_PATH.exists():
        return {}
    with open(NG_DATES_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        if not data: data = {}
        
        # Unwrap 'ng_dates' key if it exists (legacy/file format wrapper)
        if 'ng_dates' in data:
            data = data['ng_dates']
        
        # Ensure basic structure
        if 'global' not in data: data['global'] = []
        if 'by_member' not in data: data['by_member'] = {}
        if 'by_period' not in data: data['by_period'] = {}
        return data

def save_ng_dates(data: Dict[str, Any]) -> None:
    if NG_DATES_PATH.exists():
        shutil.copy(NG_DATES_PATH, NG_DATES_PATH.with_suffix('.yaml.bak'))
    else:
        NG_DATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Wrap in 'ng_dates' key only if not already present
    # (Since we unwrap in load, we usually need to wrap here)
    if 'ng_dates' not in data:
        output_data = {'ng_dates': data}
    else:
        output_data = data

    with open(NG_DATES_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(output_data, f, allow_unicode=True, default_flow_style=False)

# --- NG Dates Helpers ---

def add_global_ng_date(date_str: str) -> None:
    data = load_ng_dates()
    if date_str not in data['global']:
        data['global'].append(date_str)
        data['global'].sort()
        save_ng_dates(data)

def remove_global_ng_date(date_str: str) -> None:
    data = load_ng_dates()
    if date_str in data['global']:
        data['global'].remove(date_str)
        save_ng_dates(data)

def add_member_ng_date(member: str, date_str: str) -> None:
    data = load_ng_dates()
    if member not in data['by_member']:
        data['by_member'][member] = []
    
    if date_str not in data['by_member'][member]:
        data['by_member'][member].append(date_str)
        data['by_member'][member].sort()
        save_ng_dates(data)

def remove_member_ng_date(member: str, date_str: str) -> None:
    data = load_ng_dates()
    if member in data['by_member'] and date_str in data['by_member'][member]:
        data['by_member'][member].remove(date_str)
        # Clean up empty member
        if not data['by_member'][member]:
            del data['by_member'][member]
        save_ng_dates(data)

def add_period_ng(member: str, start: str, end: str, reason: str) -> None:
    data = load_ng_dates()
    if member not in data['by_period']:
        data['by_period'][member] = []
    
    entry = {'start': start, 'end': end, 'reason': reason}
    # Simple duplicate check
    if entry not in data['by_period'][member]:
        data['by_period'][member].append(entry)
        # Sort by start date
        data['by_period'][member].sort(key=lambda x: x['start'])
        save_ng_dates(data)

def remove_period_ng(member: str, start: str) -> None:
    data = load_ng_dates()
    if member in data['by_period']:
        data['by_period'][member] = [
            p for p in data['by_period'][member] 
            if p['start'] != start
        ]
        if not data['by_period'][member]:
            del data['by_period'][member]
        save_ng_dates(data)

def get_all_members() -> List[str]:
    """Extract all unique member names from settings"""
    settings = load_settings()
    members = set()
    
    def extract_from_group(group_list):
        if not group_list: return
        for m in group_list:
            members.add(m['name'])

    if 'members' in settings:
        m = settings['members']
        if 'day_shift' in m:
            extract_from_group(m['day_shift'].get('index_1_2_group', []))
            extract_from_group(m['day_shift'].get('index_3_group', []))
        if 'night_shift' in m:
            extract_from_group(m['night_shift'].get('index_1_group', []))
            extract_from_group(m['night_shift'].get('index_2_group', []))
            
    return sorted(list(members))


def normalize_schedule_from_client_json(
    raw: Union[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    ブラウザから送られた schedule_json を、OutputFormatter / 履歴追記用の
    schedule 辞書へ正規化する（日付キーは date、枠番号は int）。
    """
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            raise ValueError("schedule_json が空です")
        data = json.loads(raw)
    else:
        data = raw

    if not isinstance(data, dict):
        raise ValueError("schedule_json の形式が不正です")

    out: Dict[str, Any] = {"day": {}, "night": {}}

    def _clean_indexes(indexes: Any) -> Dict[int, str]:
        if not isinstance(indexes, dict):
            return {}
        norm: Dict[int, str] = {}
        for idx_raw, name in indexes.items():
            idx = int(idx_raw)
            if name is None:
                continue
            s = str(name).strip()
            if not s or s == "-":
                continue
            norm[idx] = s
        return norm

    for k, indexes in data.get("day", {}).items():
        date_key = date.fromisoformat(str(k))
        cleaned = _clean_indexes(indexes)
        if cleaned:
            out["day"][date_key] = cleaned

    for k, indexes in data.get("night", {}).items():
        date_key = date.fromisoformat(str(k))
        cleaned = _clean_indexes(indexes)
        if cleaned:
            out["night"][date_key] = cleaned

    if not out["day"] and not out["night"]:
        raise ValueError("保存できる担当行がありません（空のスケジュール）")

    return out


# --- Bulk NG Import ---

def bulk_preview_ng_dates(
    text: str, mode: str, fiscal_year: int = None
) -> List[Dict]:
    """フリーテキストをパースしてプレビュー用データを返す"""
    members = get_all_members()
    return parse_ng_text(text, members, mode=mode, fiscal_year=fiscal_year)


def bulk_apply_ng_dates(entries: List[Dict]) -> int:
    """確認済みエントリをng_dates.yamlに一括登録

    Returns: 登録した日付の件数
    """
    data = load_ng_dates()
    count = 0

    for entry in entries:
        member = entry.get("matched_name")
        dates = entry.get("resolved_dates", [])
        if not member or not dates:
            continue

        if member not in data["by_member"]:
            data["by_member"][member] = []

        for date_str in dates:
            if date_str not in data["by_member"][member]:
                data["by_member"][member].append(date_str)
                count += 1

        data["by_member"][member].sort()

    if count > 0:
        save_ng_dates(data)

    return count

# --- End Helpers ---

def _history_rows_for_template(df_page: pd.DataFrame) -> List[Dict[str, Any]]:
    """テンプレート用に日付・数値を表示しやすい形へ。"""
    rows: List[Dict[str, Any]] = []
    for _, r in df_page.iterrows():
        date_val = ""
        if "date" in r.index and pd.notna(r["date"]):
            date_val = pd.Timestamp(r["date"]).strftime("%Y-%m-%d")
        try:
            si = int(r["shift_index"]) if pd.notna(r.get("shift_index")) else 1
        except (TypeError, ValueError):
            si = 1
        pn = ""
        if "person_name" in r.index and pd.notna(r.get("person_name")):
            pn = str(r["person_name"]).strip()
        sc = ""
        if "shift_category" in r.index and pd.notna(r.get("shift_category")):
            sc = str(r["shift_category"]).strip()
        rows.append(
            {
                "date": date_val,
                "shift_category": sc,
                "shift_index": si,
                "person_name": pn,
            }
        )
    return rows


def get_history_summary(page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    empty = {
        "data": [],
        "total_count": 0,
        "total_pages": 0,
        "current_page": 1,
        "page_size": page_size,
        "has_next": False,
        "has_prev": False,
    }
    if not CSV_PATH.exists():
        return empty

    try:
        df = pd.read_csv(CSV_PATH)
        required = ["date", "shift_category", "shift_index", "person_name"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            logger.error(f"履歴CSVに必要な列がありません: {missing}")
            return empty

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date", ascending=False).reset_index(drop=True)

        total_count = len(df)
        total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0

        if page < 1:
            page = 1
        if total_pages > 0 and page > total_pages:
            page = total_pages

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]

        return {
            "data": _history_rows_for_template(df_page),
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
    except Exception as e:
        logger.error(f"Error reading history: {e}")
        return empty


def save_history_csv_page(
    page: int,
    page_size: int,
    rows: List[Dict[str, Any]],
    csv_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    履歴CSVのうち、指定ページに相当する行だけを上書き保存する。
    表示と同じく日付の降順で並べた位置（iloc）に適用する。
    """
    target = csv_path if csv_path is not None else CSV_PATH
    if not target.exists():
        return False, "CSVファイルがありません"

    required_cols = ["date", "shift_category", "shift_index", "person_name"]
    try:
        df = pd.read_csv(target)
    except Exception as e:
        return False, f"CSVの読み込みに失敗しました: {e}"

    miss = [c for c in required_cols if c not in df.columns]
    if miss:
        return False, f"必要な列がありません: {', '.join(miss)}"

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date", ascending=False).reset_index(drop=True)

    total = len(df)
    if page < 1 or page_size < 1:
        return False, "ページ指定が不正です"
    start = (page - 1) * page_size
    if start >= total:
        return False, "ページが範囲外です"

    expected_len = min(page_size, total - start)
    if len(rows) != expected_len:
        return False, f"行数が一致しません（このページは {expected_len} 行です）"

    for i, row in enumerate(rows):
        pos = start + i
        try:
            d = date.fromisoformat(str(row.get("date", "")).strip()[:10])
        except ValueError:
            return False, f"{i + 1}行目: 日付が不正です"

        cat = str(row.get("shift_category", "")).strip()
        if cat not in ("Day", "Night"):
            return False, f"{i + 1}行目: シフト区分は Day または Night を選んでください"

        try:
            idx = int(row["shift_index"])
        except (KeyError, TypeError, ValueError):
            return False, f"{i + 1}行目: Index が不正です"

        if cat == "Day" and idx not in (1, 2, 3):
            return False, f"{i + 1}行目: 日勤の Index は 1〜3 です"
        if cat == "Night" and idx not in (1, 2):
            return False, f"{i + 1}行目: 夜勤の Index は 1〜2 です"

        name = str(row.get("person_name", "")).strip()
        if not name:
            return False, f"{i + 1}行目: 担当者名を入力してください"

        df.at[pos, "date"] = pd.Timestamp(d)
        df.at[pos, "shift_category"] = cat
        df.at[pos, "shift_index"] = idx
        df.at[pos, "person_name"] = name

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy(target, target.with_suffix(".bak"))

    df.to_csv(target, index=False, encoding="utf-8-sig")
    return True, "履歴CSVを保存しました（.bak にバックアップ済み）"

def run_schedule_generation(
    start_date_str: str,
    variants: int = 1,
    variant_top_k: int = 3
) -> Tuple[bool, Any, str]:
    """
    Returns (success, result_data, message)
    """
    try:
        start_date = date.fromisoformat(start_date_str)
        _, end_date = get_rotation_period(start_date)
        
        # Check files (and attempt to copy defaults if missing)
        ensure_file_exists(SETTINGS_PATH, 'config/settings.yaml')
        ensure_file_exists(NG_DATES_PATH, 'config/ng_dates.yaml')
        
        if not SETTINGS_PATH.exists() or not NG_DATES_PATH.exists():
             return False, None, "Config files missing and could not be restored."
             
        if not CSV_PATH.exists():
             return False, None, f"History CSV not found at {CSV_PATH}. Please upload data."

        # Load data
        # Note: load_and_process_data takes path string. 
        # Since we are using local files, passing str(CSV_PATH) is correct.
        df_all, df_recent, member_stats = load_and_process_data(
            str(CSV_PATH),
            lookback_months=2
        )

        ng_dates = load_ng_dates()

        variant_count = max(1, int(variants))
        variant_top_k = max(1, int(variant_top_k))

        formatter = OutputFormatter()
        variant_results = []
        failures = []

        for variant_index in range(variant_count):
            builder = ScheduleBuilder(
                str(SETTINGS_PATH),
                str(NG_DATES_PATH),
                member_stats,
                df_recent,
                variant_index=variant_index,
                variant_top_k=variant_top_k
            )

            try:
                schedule = builder.build_schedule(start_date, end_date)

                statistics = formatter.generate_statistics(schedule, member_stats)
                analyzer = ScheduleAnalyzer(schedule, member_stats)
                analysis_result = analyzer.analyze()
                ng_status = build_ng_status_for_schedule(schedule, ng_dates)

                variant_results.append({
                    'variant_index': variant_index,
                    'schedule': schedule,
                    'statistics': statistics,
                    'analysis': analysis_result,
                    'ng_status': ng_status,
                })
            except ValueError as e:
                failures.append({
                    'variant_index': variant_index,
                    'message': str(e)
                })

        if not variant_results:
            return False, None, "すべてのバージョンでスケジュール生成に失敗しました"

        result = {
            'variants': variant_results,
            'failures': failures,
            'start_date': start_date,
            'end_date': end_date,
            'variant_count': variant_count,
            'variant_top_k': variant_top_k
        }

        return True, result, "Schedule generated successfully"
        
    except ValueError as e:
        return False, None, f"Constraint Violation: {str(e)}"
    except Exception as e:
        logger.exception("Generation error")
        return False, None, f"Unexpected Error: {str(e)}"


def get_selected_variant_result(
    start_date_str: str,
    variant_index: int = 0,
    variants: int = 1,
    variant_top_k: int = 3,
) -> Tuple[bool, Any, str]:
    """指定バリアントの生成結果を返す。"""
    success, result, message = run_schedule_generation(
        start_date_str,
        variants=variants,
        variant_top_k=variant_top_k,
    )
    if not success:
        return False, None, message

    selected = None
    for item in result["variants"]:
        if item["variant_index"] == variant_index:
            selected = item
            break

    if selected is None:
        return False, None, "選択されたバージョンが見つかりません"

    return True, {"selected": selected, "result": result}, "ok"


def save_generated_schedule(schedule: Dict, output_filename: str = None) -> str:
    if not output_filename:
        output_filename = f"schedule_{date.today().isoformat()}.csv"
    
    formatter = OutputFormatter()
    output_path = OUTPUT_DIR / output_filename
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    formatter.save_to_csv(schedule, str(output_path))
    return str(output_path)
