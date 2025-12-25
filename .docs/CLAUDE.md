# auto_arranger プロジェクト

## プロジェクト概要

### 目的
土日の日勤当番と夜勤当番を自動で組むシステムを構築します。複雑な制約条件を満たしながら、公平性を保ったローテーションを生成します。

### 対象期間
- **ローテーション期間**: 毎月21日～2ヶ月後の20日まで
- **例**: 2025年3月21日～2025年5月20日（2ヶ月間）

### 当番の種類
1. **日勤当番**: 土日のみ（3つのindexポジション）
2. **夜勤当番**: 月曜～日曜の7日間（2つのindexポジション）

---

## 技術スタック

### 言語・バージョン
- **Python**: 3.13.9（Python Install Managerで管理）
- 起動コマンド: `py -3.13 <script_name>`

### 主要ライブラリ
- **pandas** (>=2.0.0): データ処理・分析
- **PyYAML** (>=6.0): 設定ファイル管理
- **tabulate** (>=0.9.0): コンソールテーブル出力
- **python-dateutil** (>=2.8.0): 日付処理
- **pytest** (>=7.0.0): テスト

### アルゴリズム
- **Greedy Algorithm (貪欲法)**:
  - 優先度スコアベースの候補者選定
  - 制約充足チェック（Constraint Satisfaction）
  - バックトラッキングなし（高速化のため簡略化）

---

## ディレクトリ構成

```
auto_arranger/
├── main.py                      # エントリーポイント
├── config/
│   ├── settings.yaml           # メンバー・制約設定
│   └── ng_dates.yaml           # NG日設定
├── src/
│   ├── data_loader.py          # CSVデータ読み込み・前処理
│   ├── config_generator.py     # 設定ファイル自動生成
│   ├── constraint_checker.py   # 制約条件チェック
│   ├── schedule_builder.py     # スケジュール構築（Greedy）
│   └── output_formatter.py     # 結果出力・表示
├── utils/
│   ├── logger.py               # ログ設定
│   └── date_utils.py           # 日付処理ユーティリティ
├── tests/
│   ├── test_date_utils.py
│   ├── test_data_loader.py
│   ├── test_config_generator.py
│   ├── test_constraint_checker.py
│   └── test_schedule_builder.py
├── data/
│   ├── duty_roster_2021_2025.csv  # 過去の当番データ
│   └── output/                    # 生成結果出力先
├── .docs/
│   ├── AGENTS.md               # 開発者情報
│   ├── CLAUDE.md               # このファイル
│   └── update.md               # 変更履歴
├── requirements.txt
└── README.md
```

---

## 制約ルール

### 全体ルール
1. **ローテーション期間**: 21日～2ヶ月後の20日まで
2. **重複禁止**: 日勤当番と夜勤当番が同じ日にかぶることはできない
3. **夜勤後の日勤禁止**: 夜勤後の次の週には日勤当番を入れない（Min 7日）
4. **公平性**: 担当回数と期間間隔に基づく優先度スコアで調整

### 日勤当番ルール
1. **対象日**: 土日のみ
2. **Index制約**:
   - Index 1, 2グループ: 主にIndex 1, 2を担当
   - Index 3グループ: 主にIndex 3を担当
3. **間隔**: 同じ人の当番は最低14日間あける

### 夜勤ルール
1. **期間**: 月曜から日曜までの7日間勤務
2. **Index制約**:
   - Index 1グループ: Index 1のみ担当
   - Index 2グループ: Index 2のみ担当
3. **間隔**: 同じ人の当番は最低21日間あける

### 変動ルール
1. **松田さん固定**: 夜勤2に隔週で入る（基準日: 2025-02-20）
2. **NG日**: `config/ng_dates.yaml` で指定（個別日付、期間、Global休日）
3. **当番免除**: `config/settings.yaml` の `active: false` で設定

---

## 運用フロー

1. **設定調整**:
   - `config/ng_dates.yaml` にNG日・期間を追記
   - `config/settings.yaml` でメンバーの増減・免除を設定
2. **スケジュール生成**:
   ```bash
   py -3.13 main.py --start 2025-03-21
   ```
3. **確認・修正**:
   - 生成された `schedule.csv` (またはコンソール出力) を確認
   - 必要に応じて手動調整
4. **確定・履歴更新**:
   - 確定したスケジュールを `data/duty_roster_2021_2025.csv` に追記
   - 次回の生成時に過去データとして参照される

---

## 実装状況

### ✅ Phase 1: 基盤構築（完了）
- プロジェクト構造、データローダー、ユーティリティ

### ✅ Phase 2: 設定管理（完了）
- 設定ファイル自動生成、YAML管理

### ✅ Phase 3: コアロジック（完了）
- `ConstraintChecker`: 8つの制約条件の実装
- `ScheduleBuilder`: 優先度スコア計算、割当ロジック
- エラーハンドリング: 候補者不在時の詳細レポート

### ✅ Phase 4: インターフェース（完了）
- `main.py`: CLI実装
- `OutputFormatter`: テーブル表示、CSV出力、統計情報

---

## 今後の課題

1. **最適化の高度化**: 現状のGreedy法では局所最適解になる可能性があるため、将来的には数理最適化（PuLP等）への移行も検討。
2. **GUI/Web UI**: 一般ユーザー向けの操作画面。
3. **自動履歴更新**: 生成結果を自動で履歴CSVにマージする機能。
