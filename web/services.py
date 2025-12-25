import yaml
import shutil
import sys
from pathlib import Path
from datetime import date
from typing import Dict, Any, List, Tuple

import pandas as pd
from src.data_loader import load_and_process_data, DutyRosterLoader
from src.schedule_builder import ScheduleBuilder
from src.output_formatter import OutputFormatter
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
        # Ensure basic structure
        if not data: data = {}
        if 'global' not in data: data['global'] = []
        if 'by_member' not in data: data['by_member'] = {}
        if 'by_period' not in data: data['by_period'] = {}
        return data

def save_ng_dates(data: Dict[str, Any]) -> None:
    if NG_DATES_PATH.exists():
        shutil.copy(NG_DATES_PATH, NG_DATES_PATH.with_suffix('.yaml.bak'))
    else:
        NG_DATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(NG_DATES_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)

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

# --- End Helpers ---

def get_history_summary(limit: int = 50) -> List[Dict[str, Any]]:
    if not CSV_PATH.exists():
        return []
    
    try:
        df = pd.read_csv(CSV_PATH)
        # Sort by date desc
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)
        
        # Take head
        df_head = df.head(limit)
        
        # Convert to list of dicts for template
        return df_head.to_dict('records')
    except Exception as e:
        logger.error(f"Error reading history: {e}")
        return []

def run_schedule_generation(start_date_str: str) -> Tuple[bool, Any, str]:
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

        # Build
        builder = ScheduleBuilder(
            str(SETTINGS_PATH),
            str(NG_DATES_PATH),
            member_stats,
            df_recent
        )
        
        schedule = builder.build_schedule(start_date, end_date)
        
        # Stats
        formatter = OutputFormatter()
        statistics = formatter.generate_statistics(schedule, member_stats)
        
        # Prepare result for UI
        result = {
            'schedule': schedule,
            'statistics': statistics,
            'start_date': start_date,
            'end_date': end_date
        }
        
        return True, result, "Schedule generated successfully"
        
    except ValueError as e:
        return False, None, f"Constraint Violation: {str(e)}"
    except Exception as e:
        logger.exception("Generation error")
        return False, None, f"Unexpected Error: {str(e)}"

def save_generated_schedule(schedule: Dict, output_filename: str = None) -> str:
    if not output_filename:
        output_filename = f"schedule_{date.today().isoformat()}.csv"
    
    formatter = OutputFormatter()
    output_path = OUTPUT_DIR / output_filename
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    formatter.save_to_csv(schedule, str(output_path))
    return str(output_path)
