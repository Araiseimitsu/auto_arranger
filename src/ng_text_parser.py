"""
フリーテキストNG日パーサー

Googleフォーム等で集めたフリーテキスト回答を解析し、
NG日データを構造化する。
"""

import re
import unicodedata
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher


# 異字体→正規化テーブル（1文字→1文字のみ）
KANJI_NORMALIZE_TABLE = str.maketrans({
    '齋': '斉', '齊': '斉', '斎': '斉',
    '髙': '高', '﨑': '崎', '邉': '辺', '邊': '辺',
    '櫻': '桜', '澤': '沢', '濱': '浜', '廣': '広',
    '國': '国', '鷗': '鴎',
})

NAME_LABEL_PATTERN = re.compile(r'^\s*(?:名前|氏名|メンバー|担当者)\s*[:：]?\s*$')
DATE_LABEL_PATTERN = re.compile(
    r'^\s*(?:依頼日|日付|希望日|NG日|NG日程|不可日)\s*[:：]?\s*$'
)
NAME_FIELD_PATTERN = re.compile(
    r'^\s*(?:名前|氏名|メンバー|担当者)\s*[:：]\s*(.+)\s*$'
)
DATE_FIELD_PATTERN = re.compile(
    r'^\s*(?:依頼日|日付|希望日|NG日|NG日程|不可日)\s*[:：]\s*(.+)\s*$'
)


def normalize_kanji(text: str) -> str:
    """異字体を正規化"""
    return text.translate(KANJI_NORMALIZE_TABLE)


def normalize_separators(text: str) -> str:
    """区切り文字を統一してカンマに正規化"""
    # 全角→半角変換（数字・スラッシュ・カンマ）
    text = unicodedata.normalize('NFKC', text)
    # 読点→カンマ
    text = text.replace('、', ',')
    # 全角/半角スペースをカンマに（日付間の区切りとして）
    # ただし「月/日 月/日」のパターンのみ変換
    text = re.sub(r'(\d)\s+(\d)', r'\1,\2', text)
    # ピリオド区切り: 「3/7.8」→「3/7,8」
    text = re.sub(r'(\d)\.(\d)', r'\1,\2', text)
    return text.strip()


def expand_month_abbreviations(text: str) -> List[str]:
    """月省略を展開して日付文字列リストを返す

    対応:
    - M/D 形式
    - YYYY/M/D 形式
    - 月・年の省略（前要素を継承）

    例: "3/7,8,28,29" → ["3/7", "3/8", "3/28", "3/29"]
    例: "3/7,4/1,2" → ["3/7", "4/1", "4/2"]
    例: "2026/12/28,29,2027/1/4" → ["2026/12/28", "2026/12/29", "2027/1/4"]
    """
    parts = [p.strip() for p in text.split(',') if p.strip()]
    result = []
    current_year: Optional[str] = None
    current_month: Optional[str] = None

    for part in parts:
        if '/' in part:
            segments = [s.strip() for s in part.split('/')]

            # YYYY/M/D
            if len(segments) == 3:
                current_year, current_month, day_part = segments
                result.append(f"{current_year}/{current_month}/{day_part}")
                continue

            # M/D
            if len(segments) == 2:
                current_month, day_part = segments
                if current_year is not None:
                    result.append(f"{current_year}/{current_month}/{day_part}")
                else:
                    result.append(f"{current_month}/{day_part}")
                continue

        if current_month and part.isdigit():
            if current_year is not None:
                result.append(f"{current_year}/{current_month}/{part}")
            else:
                result.append(f"{current_month}/{part}")

    return result


def resolve_year(month: int, day: int, year: int) -> Optional[date]:
    """年・月・日からdateを生成（不正日付はNone）。"""
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _is_year_rollover(previous_month: int, current_month: int) -> bool:
    """年跨ぎとみなす月遷移かを判定する。

    12月→1月などは翌年に進める。
    入力順が不規則なケースで過剰に翌年化しないよう、一定条件でのみ判定する。
    """
    if current_month >= previous_month:
        return False

    if previous_month >= 10 and current_month <= 3:
        return True

    if previous_month - current_month >= 6:
        return True

    return False


def _normalize_year(raw_year: int) -> int:
    """2桁年は2000年代として補完する。"""
    if raw_year < 100:
        return 2000 + raw_year
    return raw_year


def _parse_date_token(token: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """日付トークンを (year, month, day) へ分解する。

    year は未指定時 None。
    """
    try:
        segments = [int(s.strip()) for s in token.split('/')]
    except ValueError:
        return None, None, None

    if len(segments) == 3:
        y, m, d = segments
        return y, m, d

    if len(segments) == 2:
        m, d = segments
        return None, m, d

    return None, None, None


def parse_date_strings(
    date_strings: List[str], fiscal_year: int
) -> List[Optional[date]]:
    """日付文字列リストをdateオブジェクトに変換する。

    年未指定（M/D）は、fiscal_year を基準年として解釈し、
    12月→1月などの年跨ぎを入力順から自動判定する。
    """
    results = []
    current_year = fiscal_year
    previous_month: Optional[int] = None

    for ds in date_strings:
        raw_year, month, day = _parse_date_token(ds)
        if month is None or day is None:
            results.append(None)
            continue

        if raw_year is not None:
            current_year = _normalize_year(raw_year)
        elif previous_month is not None and _is_year_rollover(previous_month, month):
            current_year += 1

        resolved = resolve_year(month, day, current_year)
        results.append(resolved)

        if resolved is not None:
            previous_month = month

    return results


def expand_weekly(start_date: date) -> List[date]:
    """月曜日から7日間を展開（夜勤用）"""
    return [start_date + timedelta(days=i) for i in range(7)]


def fuzzy_match_name(
    input_name: str, known_names: List[str], threshold: float = 0.5
) -> Tuple[Optional[str], float]:
    """名前のファジーマッチング

    マッチ戦略（優先順）:
    1. 完全一致
    2. 前方一致（最長マッチ）
    3. 正規化後の完全一致
    4. 正規化後の前方一致
    5. SequenceMatcherによる類似度

    Returns: (マッチした名前, 信頼度0.0-1.0)
    """
    if not input_name:
        return None, 0.0

    stripped = input_name.strip()

    # 1. 完全一致
    if stripped in known_names:
        return stripped, 1.0

    # 2. 入力が既知名で始まる（「新井翔太」→「新井翔」、最長マッチ優先）
    prefix_matches = [n for n in known_names if stripped.startswith(n)]
    if prefix_matches:
        best = max(prefix_matches, key=len)
        return best, 0.95

    # 3. 既知名が入力で始まる（「加藤」→「加藤凌」、最短マッチ優先）
    reverse_matches = [n for n in known_names if n.startswith(stripped)]
    if reverse_matches:
        best = min(reverse_matches, key=len)
        return best, 0.9

    # 4. 正規化後のマッチング
    norm_input = normalize_kanji(stripped)
    for name in known_names:
        norm_name = normalize_kanji(name)
        if norm_input == norm_name:
            return name, 0.95
        if norm_input.startswith(norm_name):
            return name, 0.9
        if norm_name.startswith(norm_input):
            return name, 0.85

    # 5. SequenceMatcherによる類似度
    best_match = None
    best_ratio = 0.0
    for name in known_names:
        ratio = SequenceMatcher(None, norm_input, normalize_kanji(name)).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = name

    if best_ratio >= threshold:
        return best_match, round(best_ratio, 2)

    return None, 0.0


def _is_date_line(line: str) -> bool:
    """日付を含む行かどうか判定"""
    return bool(re.search(r'\d+\s*/\s*\d+', line))


def _extract_labeled_value(line: str, pattern: re.Pattern) -> Optional[str]:
    """`ラベル: 値` 形式から値のみ抽出"""
    match = pattern.match(line)
    if not match:
        return None
    value = match.group(1).strip()
    return value if value else None


def _normalize_input_lines(text: str) -> List[str]:
    """ラベル行を除去・正規化してパース対象行を作る"""
    raw_lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    normalized = []

    for line in raw_lines:
        name_value = _extract_labeled_value(line, NAME_FIELD_PATTERN)
        if name_value is not None:
            normalized.append(name_value)
            continue

        date_value = _extract_labeled_value(line, DATE_FIELD_PATTERN)
        if date_value is not None:
            normalized.append(date_value)
            continue

        if NAME_LABEL_PATTERN.match(line) or DATE_LABEL_PATTERN.match(line):
            continue

        normalized.append(line)

    return normalized


def _is_name_line(line: str) -> bool:
    """名前行かどうか判定（日付を含まず、日本語文字を含む）"""
    if _is_date_line(line):
        return False
    if NAME_LABEL_PATTERN.match(line) or DATE_LABEL_PATTERN.match(line):
        return False
    # 日本語文字（漢字・ひらがな・カタカナ）を含む
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', line))


def parse_text_blocks(text: str) -> List[Dict[str, str]]:
    """テキストを「日付 + 名前」のブロックに分割

    対応フォーマット:
    - 名前→日付（従来）
    - 日付→名前（従来）
    - 日付→複数名前（1日付に複数行の名前）

    Returns: [{"dates": "3/7,8", "names": "田中"}, ...]
    """
    lines = _normalize_input_lines(text)
    blocks: List[Dict[str, str]] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # パターン1: 日付行の後に名前行が続く（複数行対応）
        if _is_date_line(line):
            date_line = line
            i += 1
            name_lines = []
            while i < n and _is_name_line(lines[i]) and not _is_date_line(lines[i]):
                name_lines.append(lines[i])
                i += 1

            if name_lines:
                for name_line in name_lines:
                    blocks.append({"dates": date_line, "names": name_line})
            else:
                blocks.append({"dates": date_line, "names": ""})
            continue

        # パターン2: 名前行の後に日付行が続く（複数行名前→1日付対応）
        if _is_name_line(line):
            name_lines = [line]
            i += 1
            while i < n and _is_name_line(lines[i]) and not _is_date_line(lines[i]):
                name_lines.append(lines[i])
                i += 1

            if i < n and _is_date_line(lines[i]):
                date_line = lines[i]
                i += 1
                for name_line in name_lines:
                    blocks.append({"dates": date_line, "names": name_line})
            continue

        i += 1

    return blocks


def parse_names(name_text: str) -> List[str]:
    """名前テキストをパースして名前リストを返す"""
    if not name_text:
        return []
    # 区切り文字を正規化
    normalized = name_text.replace('、', ',').replace('，', ',')
    normalized = re.sub(r'\s+', ',', normalized)
    names = [n.strip() for n in normalized.split(',') if n.strip()]
    return names


def parse_ng_text(
    text: str,
    known_members: List[str],
    mode: str = 'daily',
    fiscal_year: int = None,
) -> List[Dict]:
    """フリーテキストをパースしてNG日エントリのリストを返す

    Args:
        text: パース対象のフリーテキスト
        known_members: settings.yamlから取得したメンバー名リスト
        mode: 'daily'(個別日付) / 'weekly'(月曜→7日間展開)
        fiscal_year: 基準年（Noneの場合、現在年を使用）

    Returns: [
        {
            "input_name": "新井翔太",
            "matched_name": "新井翔",
            "confidence": 0.95,
            "input_dates": "3/7,8",
            "resolved_dates": ["2026-03-07", "2026-03-08"],
            "selected": True
        },
        ...
    ]
    """
    if fiscal_year is None:
        fiscal_year = date.today().year

    blocks = parse_text_blocks(text)
    entries = []

    for block in blocks:
        # 日付のパース
        normalized_dates = normalize_separators(block["dates"])
        date_strings = expand_month_abbreviations(normalized_dates)
        parsed_dates = parse_date_strings(date_strings, fiscal_year)

        # weekly モードの場合、各日付を月曜日として7日間展開
        if mode == 'weekly':
            expanded = []
            for d in parsed_dates:
                if d is not None:
                    expanded.extend(expand_weekly(d))
            parsed_dates = expanded

        # 有効な日付のみ
        valid_dates = [d for d in parsed_dates if d is not None]
        date_strs = sorted(set(d.isoformat() for d in valid_dates))

        # 名前のパース
        names = parse_names(block["names"])
        if not names:
            names = [""]

        for name in names:
            matched, confidence = fuzzy_match_name(name, known_members)
            entries.append({
                "input_name": name,
                "matched_name": matched,
                "confidence": confidence,
                "input_dates": block["dates"],
                "resolved_dates": date_strs,
                "selected": confidence >= 0.7 and len(date_strs) > 0,
            })

    return entries
