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
- **PuLP** (>=2.7.0): 線形計画法による最適化
- **PyYAML** (>=6.0): 設定ファイル管理
- **tabulate** (>=0.9.0): コンソールテーブル出力
- **python-dateutil** (>=2.8.0): 日付処理
- **pytest** (>=7.0.0): テスト

---

## ディレクトリ構成

```
auto_arranger/
├── main.py                      # エントリーポイント（未実装）
├── config/
│   ├── settings.yaml           # メンバー・制約設定
│   └── ng_dates.yaml           # NG日設定
├── src/
│   ├── data_loader.py          # CSVデータ読み込み・前処理
│   ├── config_generator.py     # 設定ファイル自動生成
│   ├── member_manager.py       # メンバー情報管理（未実装）
│   ├── constraint_checker.py   # 制約条件チェック（未実装）
│   ├── optimizer.py            # PuLP最適化エンジン（未実装）
│   ├── schedule_generator.py   # スケジュール生成統括（未実装）
│   └── output_formatter.py     # 結果出力・表示（未実装）
├── utils/
│   ├── logger.py               # ログ設定
│   └── date_utils.py           # 日付処理ユーティリティ
├── tests/
│   ├── test_date_utils.py      # 日付ユーティリティテスト
│   ├── test_data_loader.py     # データローダーテスト
│   └── test_config_generator.py # 設定生成テスト
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
3. **夜勤後の日勤禁止**: 夜勤後の次の週には日勤当番を入れない
4. **公平性**: 回数はなるべく公平を維持

### 日勤当番ルール
1. **対象日**: 土日のみ
2. **Index制約**:
   - 直近2か月でindex 1または2に該当した人 → index 3には配置不可
   - 直近2か月でindex 3に該当した人 → index 1,2には配置不可
3. **ローテーション**: 同じ人の当番はできる限り期間をあける

### 夜勤ルール
1. **期間**: 月曜から日曜までの7日間勤務
2. **Index制約**:
   - 夜勤index 1の人 → 夜勤index 2になることができない
   - 夜勤index 2の人 → 夜勤index 1になることができない
3. **メンバー**: 直近2か月で夜勤を担当している人をメンバーとする
4. **ローテーション**: 同じ人の次の夜勤当番まではなるべく期間をあける

### 変動ルール
1. **松田さん固定**: 夜勤2に隔週で入る
2. **NG日**: 当番に入れない日を事前申請可能

---

## データ分析結果

### 過去データ（duty_roster_2021_2025.csv）
- **期間**: 2021年10月21日～2025年2月20日
- **総レコード数**: 3,501行（元データ）→ 3,319行（クリーニング後）
- **重複除去**: 179行
- **無効データ除去**: 3行（"-", "変更→", "person_name"）

### アクティブメンバー（直近2ヶ月）
- **総メンバー数**: 22名
- **直近データ**: 142レコード

### メンバー分類（過去2ヶ月の実績より自動判定）
- **日勤 index 1,2グループ**: 16名
- **日勤 index 3グループ**: 5名
- **夜勤 index 1グループ**: 9名
- **夜勤 index 2グループ**: 5名（松田さん含む）

### 松田さんの特別設定
- **出現回数**: 376回（全データの約10.7%）
- **配置パターン**: 夜勤 index 2のみに固定
- **パターン**: 隔週（biweekly）
- **基準日**: 2025-02-20（過去データから自動検出）

---

## 設定ファイル

### config/settings.yaml
メンバー情報、制約条件、松田さんの隔週パターンなどを管理。

**初回起動時**: 過去2ヶ月のデータから自動生成される
**2回目以降**: 既存のsettings.yamlを使用（手動編集可能）

主要設定項目:
- `members`: メンバー情報（日勤/夜勤、indexグループ別）
- `matsuda_schedule`: 松田さんの隔週パターン
- `constraints`: 制約条件（公平性、間隔、重複禁止等）
- `historical_data`: 過去データ参照設定
- `output`: 出力形式設定

### config/ng_dates.yaml
当番に入れない日の設定。

設定方法:
- `by_member`: メンバー別のNG日（日付リスト）
- `global`: 全体NG日（祝日等）
- `by_period`: 期間指定のNG日（休暇等）

---

## 使用方法

### 初回セットアップ
```bash
# 仮想環境作成（推奨）
py -3.13 -m venv .venv
.venv\Scripts\activate

# ライブラリインストール
py -3.13 -m pip install -r requirements.txt

# 設定ファイル自動生成（初回のみ）
py -3.13 test_config_gen.py
```

### 設定ファイル確認・編集
1. `config/settings.yaml` を開いて内容を確認
2. 必要に応じてメンバー情報やactive状態を編集
3. `config/ng_dates.yaml` でNG日を設定

### スケジュール生成（未実装）
```bash
# 例: 2025年3月21日～5月20日のスケジュール生成
py -3.13 main.py --start 2025-03-21 --end 2025-05-20

# デバッグモード
py -3.13 main.py --start 2025-03-21 --end 2025-05-20 --debug
```

---

## テスト

### テスト実行
```bash
# 全テスト実行
py -3.13 -m pytest tests/ -v

# 特定のテストのみ
py -3.13 -m pytest tests/test_date_utils.py -v
```

### テストカバレッジ
- **date_utils.py**: 7テスト（日付処理）
- **data_loader.py**: 6テスト（データ読み込み・クリーニング）
- **config_generator.py**: 5テスト（設定ファイル生成）
- **合計**: 18テスト（全てパス）

---

## 実装状況

### ✅ Phase 1: 基盤構築（完了）
- [x] プロジェクト構造作成
- [x] requirements.txt作成
- [x] utils/logger.py実装
- [x] utils/date_utils.py実装
- [x] src/data_loader.py実装

### ✅ Phase 2: 設定管理（完了）
- [x] src/config_generator.py実装
- [x] config/settings.yaml自動生成
- [x] config/ng_dates.yaml雛形生成

### ✅ テスト（完了）
- [x] tests/test_date_utils.py作成
- [x] tests/test_data_loader.py作成
- [x] tests/test_config_generator.py作成
- [x] 全テスト実行・パス確認

### 🚧 Phase 3以降（未実装）
- [ ] src/member_manager.py実装
- [ ] src/constraint_checker.py実装
- [ ] src/optimizer.py実装（PuLP最適化エンジン）
- [ ] src/schedule_generator.py実装
- [ ] src/output_formatter.py実装
- [ ] main.py実装（エントリーポイント）

---

## 制約充足問題の定式化（予定）

### 変数定義
- **日勤変数**: `x[d, m, i] ∈ {0, 1}` (日付、メンバー、index)
- **夜勤変数**: `y[w, m, i] ∈ {0, 1}` (週、メンバー、index)

### 目的関数
```
Minimize: 担当回数の最大値 - 担当回数の最小値
（公平性を最大化）
```

### 主要制約条件
1. 各日・各indexに1人のみ割り当て
2. Index制約（過去2ヶ月の実績に基づく）
3. 日勤・夜勤重複禁止
4. 夜勤後7日間は日勤禁止
5. NG日制約
6. 松田さん隔週固定制約

---

## コード品質管理

### リファクタリング方針
- **コード重複**: 発見次第排除
- **モジュール化**: 単一責任の原則（SRP）
- **ファイル行数**: 1ファイル1000行以内を推奨
- **共通処理**: ユーティリティとして分離

### デバッグ
- **ログ出力**: 詳細なログでバグ原因特定
- **デバッグモード**: 必要時に有効化、修正後は無効化

---

## 関連ドキュメント
- [AGENTS.md](AGENTS.md): 開発者情報
- [update.md](update.md): 変更履歴
- [README.md](../README.md): プロジェクト概要・使い方

---

## 連絡先
プロジェクトに関する質問や提案は、AGENTS.mdを参照してください。
