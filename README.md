# auto_arranger - 当番自動生成システム

土日の日勤当番と夜勤当番を自動で組むシステムです。複雑な制約条件を満たしながら、公平性を保ったローテーションを生成します。

## 特徴

- ✅ **過去データからの自動設定**: 直近2ヶ月のデータから初期設定を自動生成
- ✅ **複雑な制約対応**: 11種類以上の制約条件を同時に満たす
- ✅ **公平性保証**: 優先度スコアと間隔制約により最適化
- ✅ **柔軟な設定**: YAMLファイルで簡単にカスタマイズ可能
- ✅ **NG日管理**: メンバー別・期間別にNG日を設定可能

## クイックスタート

### 1. セットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd auto_arranger

# 仮想環境作成（推奨）
py -3.13 -m venv .venv
.venv\Scripts\activate

# 依存ライブラリインストール
py -3.13 -m pip install -r requirements.txt
```

### 2. 初期設定生成

```bash
# 過去データから設定ファイルを自動生成
py -3.13 test_config_gen.py
```

実行後、以下のファイルが生成されます:
- `config/settings.yaml`: メンバー設定と制約条件
- `config/ng_dates.yaml`: NG日設定の雛形

### 3. 設定ファイルの確認・編集

#### config/settings.yaml
メンバーの情報や制約条件を確認・編集できます:
- メンバーのactive状態（true/false）
- 制約パラメータ（公平性、間隔等）

#### config/ng_dates.yaml
当番に入れない日を設定します:
```yaml
ng_dates:
  by_member:
    山田太郎:
      - "2025-03-15"
      - "2025-03-16"
  global:
    - "2025-01-01"  # 元日
  by_period:
    鈴木花子:
      - start: "2025-08-10"
        end: "2025-08-20"
        reason: "夏季休暇"
```

### 4. スケジュール生成

```bash
# 例: 2025年3月21日からのスケジュール生成
py -3.13 main.py --start 2025-03-21

# CSV出力する場合
py -3.13 main.py --start 2025-03-21 --output schedule.csv
```

---

## 制約ルール

### 日勤当番
- 土日のみ
- 3つのindexポジション
- 直近2ヶ月のindex履歴に基づく配置制限

### 夜勤当番
- 月曜～日曜の7日間
- 2つのindexポジション
- 松田さんは夜勤2に隔週で固定

### その他の制約
- 日勤と夜勤が同じ日に重複不可
- 夜勤終了後7日間は日勤不可
- NG日には割り当てない
- 担当回数の公平性を保つ

詳細は [.docs/CLAUDE.md](.docs/CLAUDE.md) を参照してください。

---

## プロジェクト構成

```
auto_arranger/
├── config/              # 設定ファイル
├── src/                 # ソースコード
├── utils/               # ユーティリティ
├── tests/               # テスト
├── data/                # データファイル
└── .docs/               # ドキュメント
```

---

## 技術スタック

- **Python**: 3.13.9
- **pandas**: データ処理
- **PyYAML**: 設定管理
- **pytest**: テスト

---

## 開発状況

### ✅ 完了
- [x] Phase 1: 基盤構築（データ処理、日付処理）
- [x] Phase 2: 設定管理（自動生成機能）
- [x] Phase 3: 制約チェッカー・スケジュール構築（Greedy）
- [x] Phase 4: CLI・結果出力
- [x] テスト実装（18テスト、100%パス）
- [x] ドキュメント整備

---

## テスト

```bash
# 全テスト実行
py -3.13 -m pytest tests/ -v

# 特定のテストのみ
py -3.13 -m pytest tests/test_date_utils.py -v
```

**テスト結果**: 18/18 パス（100%）

---

## ドキュメント

- [CLAUDE.md](.docs/CLAUDE.md): 詳細なプロジェクト説明
- [update.md](.docs/update.md): 変更履歴
- [AGENTS.md](.docs/AGENTS.md): 開発者情報

---

## ライセンス

このプロジェクトは個人使用を目的としています。

---

## 連絡先

プロジェクトに関する質問や提案は、[.docs/AGENTS.md](.docs/AGENTS.md)を参照してください。
