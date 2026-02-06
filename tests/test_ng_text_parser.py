"""
フリーテキストNG日パーサーのテスト
"""

import pytest
from datetime import date
from src.ng_text_parser import (
    normalize_separators,
    expand_month_abbreviations,
    resolve_year,
    parse_date_strings,
    expand_weekly,
    fuzzy_match_name,
    normalize_kanji,
    parse_text_blocks,
    parse_names,
    parse_ng_text,
)


# --- 区切り文字正規化 ---

class TestNormalizeSeparators:
    def test_comma_passthrough(self):
        assert normalize_separators("3/7,3/8") == "3/7,3/8"

    def test_japanese_comma(self):
        result = normalize_separators("3/7、3/8")
        assert result == "3/7,3/8"

    def test_period_separator(self):
        result = normalize_separators("3/7.8")
        assert result == "3/7,8"

    def test_fullwidth_space(self):
        result = normalize_separators("2/28\u30003/1")
        assert result == "2/28,3/1"

    def test_halfwidth_space(self):
        result = normalize_separators("3/7 3/8")
        assert result == "3/7,3/8"

    def test_fullwidth_numbers(self):
        """全角数字が半角に変換される"""
        result = normalize_separators("３/７,８")
        assert result == "3/7,8"

    def test_mixed_separators(self):
        result = normalize_separators("3/7、3/8 3/9.10")
        assert "3/7" in result
        assert "3/8" in result


# --- 月省略展開 ---

class TestExpandMonthAbbreviations:
    def test_simple_dates(self):
        result = expand_month_abbreviations("3/7,3/8")
        assert result == ["3/7", "3/8"]

    def test_month_abbreviation(self):
        result = expand_month_abbreviations("3/7,8,28,29")
        assert result == ["3/7", "3/8", "3/28", "3/29"]

    def test_multiple_months(self):
        result = expand_month_abbreviations("3/7,8,4/1,2")
        assert result == ["3/7", "3/8", "4/1", "4/2"]

    def test_single_date(self):
        result = expand_month_abbreviations("12/25")
        assert result == ["12/25"]

    def test_empty(self):
        result = expand_month_abbreviations("")
        assert result == []


# --- 年推定 ---

class TestResolveYear:
    def test_april_to_december_uses_fiscal_year(self):
        d = resolve_year(4, 1, 2025)
        assert d == date(2025, 4, 1)

        d = resolve_year(12, 31, 2025)
        assert d == date(2025, 12, 31)

    def test_january_to_march_uses_next_year(self):
        d = resolve_year(1, 15, 2025)
        assert d == date(2026, 1, 15)

        d = resolve_year(3, 31, 2025)
        assert d == date(2026, 3, 31)

    def test_invalid_date_returns_none(self):
        d = resolve_year(2, 30, 2025)
        assert d is None


class TestParseDateStrings:
    def test_basic(self):
        result = parse_date_strings(["3/7", "3/8"], fiscal_year=2025)
        assert result == [date(2026, 3, 7), date(2026, 3, 8)]

    def test_cross_fiscal_year(self):
        result = parse_date_strings(["12/25", "1/10"], fiscal_year=2025)
        assert result == [date(2025, 12, 25), date(2026, 1, 10)]

    def test_invalid(self):
        result = parse_date_strings(["abc"], fiscal_year=2025)
        assert result == [None]


# --- weekly展開 ---

class TestExpandWeekly:
    def test_expand_7_days(self):
        monday = date(2026, 3, 2)
        result = expand_weekly(monday)
        assert len(result) == 7
        assert result[0] == date(2026, 3, 2)
        assert result[6] == date(2026, 3, 8)


# --- 名前マッチング ---

class TestFuzzyMatchName:
    @pytest.fixture
    def known_names(self):
        return ["丸岡", "加藤凌", "大関", "塩田", "新井翔", "高橋良", "松田"]

    def test_exact_match(self, known_names):
        name, conf = fuzzy_match_name("丸岡", known_names)
        assert name == "丸岡"
        assert conf == 1.0

    def test_fullname_to_short(self, known_names):
        """フルネーム→省略名（前方一致）"""
        name, conf = fuzzy_match_name("新井翔太", known_names)
        assert name == "新井翔"
        assert conf >= 0.9

    def test_kanji_normalization(self, known_names):
        """異字体の正規化"""
        names_with_variant = ["斉藤", "高橋良"]
        name, conf = fuzzy_match_name("齋藤", names_with_variant)
        assert name == "斉藤"
        assert conf >= 0.9

    def test_takahashi_variant(self):
        """髙橋→高橋"""
        names = ["高橋良"]
        name, conf = fuzzy_match_name("髙橋良", names)
        assert name == "高橋良"
        assert conf >= 0.9

    def test_no_match(self, known_names):
        name, conf = fuzzy_match_name("存在しない名前", known_names)
        assert conf < 0.5

    def test_empty_input(self, known_names):
        name, conf = fuzzy_match_name("", known_names)
        assert name is None
        assert conf == 0.0

    def test_partial_input_matches_longer(self, known_names):
        """短い入力が長い名前にマッチ"""
        name, conf = fuzzy_match_name("加藤", known_names)
        assert name == "加藤凌"
        assert conf >= 0.85


# --- 異字体正規化 ---

class TestNormalizeKanji:
    def test_saitou(self):
        assert normalize_kanji("齋藤") == "斉藤"

    def test_takahashi(self):
        assert normalize_kanji("髙橋") == "高橋"

    def test_no_change(self):
        assert normalize_kanji("田中") == "田中"


# --- テキストブロック分割 ---

class TestParseTextBlocks:
    def test_name_then_date(self):
        """名前→日付の順（主要パターン）"""
        text = "田中、佐藤\n3/7,8"
        blocks = parse_text_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["names"] == "田中、佐藤"
        assert blocks[0]["dates"] == "3/7,8"

    def test_multiple_blocks(self):
        text = "田中\n3/7,8\n山田\n3/14,15"
        blocks = parse_text_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]["names"] == "田中"
        assert blocks[1]["names"] == "山田"

    def test_date_then_name_fallback(self):
        """日付→名前の順（フォールバック）"""
        text = "3/7,8\n田中"
        blocks = parse_text_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["dates"] == "3/7,8"
        assert blocks[0]["names"] == "田中"

    def test_empty_text(self):
        blocks = parse_text_blocks("")
        assert blocks == []

    def test_date_only_no_name(self):
        """名前なしの日付行"""
        text = "3/7,8"
        blocks = parse_text_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["names"] == ""

    def test_label_lines_name_then_date(self):
        """`名前` / `依頼日` ラベル行を含む入力"""
        text = "名前\n田中\n依頼日\n3/7,8\n名前\n佐藤\n依頼日\n3/14"
        blocks = parse_text_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]["names"] == "田中"
        assert blocks[0]["dates"] == "3/7,8"
        assert blocks[1]["names"] == "佐藤"
        assert blocks[1]["dates"] == "3/14"

    def test_inline_labels_name_then_date(self):
        """`名前: xxx` / `依頼日: xxx` 形式"""
        text = "名前: 田中\n依頼日: 3/7,8\n名前: 佐藤\n依頼日: 3/14"
        blocks = parse_text_blocks(text)
        assert len(blocks) == 2
        assert blocks[0]["names"] == "田中"
        assert blocks[0]["dates"] == "3/7,8"
        assert blocks[1]["names"] == "佐藤"
        assert blocks[1]["dates"] == "3/14"

    def test_date_then_multiple_name_lines(self):
        """日付行の後に複数の名前行が続くケース"""
        text = "2/23\n加藤凌司\n大関慎也\n木村宗一郎\n3/2\n丸岡光輝\n新井洋介"
        blocks = parse_text_blocks(text)
        assert len(blocks) == 5
        assert blocks[0] == {"dates": "2/23", "names": "加藤凌司"}
        assert blocks[1] == {"dates": "2/23", "names": "大関慎也"}
        assert blocks[2] == {"dates": "2/23", "names": "木村宗一郎"}
        assert blocks[3] == {"dates": "3/2", "names": "丸岡光輝"}
        assert blocks[4] == {"dates": "3/2", "names": "新井洋介"}

    def test_date_then_multiple_name_lines_with_multi_dates(self):
        """1名に対して複数日付指定（日付行→名前行）"""
        text = "2/23、3/23、4/20\n矢野祐次\n4/20\n髙橋拓未\n3/2、4/13\n幅下孝一"
        blocks = parse_text_blocks(text)
        assert len(blocks) == 3
        assert blocks[0] == {"dates": "2/23、3/23、4/20", "names": "矢野祐次"}
        assert blocks[1] == {"dates": "4/20", "names": "髙橋拓未"}
        assert blocks[2] == {"dates": "3/2、4/13", "names": "幅下孝一"}


# --- 名前パース ---

class TestParseNames:
    def test_comma_separated(self):
        assert parse_names("田中,佐藤") == ["田中", "佐藤"]

    def test_japanese_comma(self):
        assert parse_names("田中、佐藤") == ["田中", "佐藤"]

    def test_space_separated(self):
        assert parse_names("田中 佐藤") == ["田中", "佐藤"]

    def test_single_name(self):
        assert parse_names("田中") == ["田中"]

    def test_empty(self):
        assert parse_names("") == []


# --- 統合テスト ---

class TestParseNgText:
    @pytest.fixture
    def members(self):
        return ["丸岡", "加藤凌", "大関", "塩田", "新井翔", "高橋良", "松田"]

    def test_daily_mode(self, members):
        text = "丸岡、大関\n3/7,8"
        entries = parse_ng_text(text, members, mode='daily', fiscal_year=2025)
        assert len(entries) == 2
        # 丸岡
        assert entries[0]["matched_name"] == "丸岡"
        assert entries[0]["confidence"] == 1.0
        assert "2026-03-07" in entries[0]["resolved_dates"]
        assert "2026-03-08" in entries[0]["resolved_dates"]
        assert entries[0]["selected"] is True

    def test_weekly_mode(self, members):
        text = "松田\n3/2"
        entries = parse_ng_text(text, members, mode='weekly', fiscal_year=2025)
        assert len(entries) == 1
        # 月曜日3/2から7日間展開
        assert len(entries[0]["resolved_dates"]) == 7

    def test_unknown_name(self, members):
        text = "XXXXX\n3/7"
        entries = parse_ng_text(text, members, mode='daily', fiscal_year=2025)
        assert len(entries) == 1
        assert entries[0]["confidence"] < 0.7
        assert entries[0]["selected"] is False

    def test_fullname_resolution(self, members):
        text = "新井翔太\n3/7"
        entries = parse_ng_text(text, members, mode='daily', fiscal_year=2025)
        assert entries[0]["matched_name"] == "新井翔"
        assert entries[0]["confidence"] >= 0.9

    def test_multiple_blocks(self, members):
        text = "丸岡\n3/7,8\n塩田、高橋良\n4/1,2,3"
        entries = parse_ng_text(text, members, mode='daily', fiscal_year=2025)
        assert len(entries) == 3
        assert entries[0]["matched_name"] == "丸岡"
        assert entries[1]["matched_name"] == "塩田"
        assert entries[2]["matched_name"] == "高橋良"

    def test_fiscal_year_auto_detection(self, members):
        """fiscal_year=Noneで自動推定"""
        text = "丸岡\n3/7"
        entries = parse_ng_text(text, members, mode='daily')
        assert len(entries) == 1
        assert len(entries[0]["resolved_dates"]) > 0
