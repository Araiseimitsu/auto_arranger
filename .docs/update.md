# 変更履歴

このファイルには、プロジェクトの重要な変更や更新を記録します。

---

## 2026-02-06: NG一括登録パーサーの入力ゆれ耐性を強化

### 変更内容

- `src/ng_text_parser.py` を拡張し、以下の入力形式を自動解釈できるよう改善
  - 日付範囲: `3/7-9`, `3/7〜3/9`, `3/7~3/9`, `3/30~4/2`
  - 和文日付: `3月7日`, `2026年3月7日`
  - 曜日注釈付き: `3/7(土)`, `3月8日（日）`
  - 1行混在: `今井敬史 3/7,3/8` / `3/7,3/8 今井敬史`
  - 既存の `.` 区切り（`3/7. 3/8`）も継続対応
- 日付行判定を `/` 形式以外にも拡張し、ブロック分割の取りこぼしを低減
- 不自然な長大範囲の誤入力対策として、範囲展開は最大63日までに制限

### 変更ファイル

- `src/ng_text_parser.py`
- `tests/test_ng_text_parser.py`

### テスト

- `py -3 -m pytest tests/test_ng_text_parser.py -q`（63 passed）
- `py -3 -m pytest -q`（既存テスト1件失敗: `tests/test_schedule_builder.py::test_calculate_priority_score_no_history`）

---

## 2026-02-06: NG一括登録の「ピリオド+空白」日付区切りを修正

### 変更内容

- `src/ng_text_parser.py` の `normalize_separators` を修正し、`3/7. 3/8. 3/21. 3/22` のような `.` 区切り（空白あり/なし、全角句点含む）をカンマ区切りとして正しく解釈
- これにより、プレビューで `resolved_dates` が `-` になっていた行（例: 今井敬史）が自動選択されて一括登録できるよう改善
- `tests/test_ng_text_parser.py` に回帰テストを追加（区切り正規化テスト、実際の入力形式での統合テスト）

### 変更ファイル

- `src/ng_text_parser.py`
- `tests/test_ng_text_parser.py`

### テスト

- `py -3 -m pytest tests/test_ng_text_parser.py -q`（56 passed）

---

## 2026-02-06: 印刷向けカレンダー結果ページを追加

### 変更内容

- 当番表の各バリアントに `カレンダー表示` ボタンを追加し、専用ページ `/print/calendar` を開けるように変更
- `src/calendar_view.py` を追加し、生成済みスケジュール（日勤/夜勤）とNG設定（全体/個別/期間）をカレンダー表示データへ変換
- 印刷専用テンプレート `web/templates/print_calendar.html` を追加し、月次カレンダーと出勤不可一覧（全体NG・日別・個別・期間）を表示
- 印刷専用スタイル `web/static/css/print_calendar.css` と印刷ボタン処理 `web/static/js/print_calendar.js` を追加
- `web/services.py` にバリアント選択共通処理 `get_selected_variant_result` を追加し、`save_result` と印刷ルートで再利用

### 変更ファイル

- `src/calendar_view.py`
- `tests/test_calendar_view.py`
- `web/routes.py`
- `web/services.py`
- `web/templates/components/schedule_variant.html`
- `web/templates/print_calendar.html`
- `web/static/css/print_calendar.css`
- `web/static/js/print_calendar.js`
- `web/static/css/style.css`
- `web/templates/base.html`

### テスト

- `py -3 -m pytest tests/test_calendar_view.py -q`（3 passed）
- `py -3 -m pytest tests/test_ng_status_view.py -q`（5 passed）
- `py -3 -m pytest -q`（既存テスト1件失敗: `tests/test_schedule_builder.py::test_calculate_priority_score_no_history`）

---

## 2026-02-06: NG日程タブ戻り不具合を追加修正（HTMX更新時）

### 変更内容

- `web/templates/components/ng_dates_form.html` の NG 操作フォームを `hx-swap="outerHTML"` に統一し、`#ng-dates-container` の入れ子化を防止
- 一括適用 (`htmx.ajax`) も `swap: 'outerHTML'` に変更
- `web/static/js/app.js` に `htmx:afterSwap` フックを追加し、NG画面更新後に `restoreNgTab()` を再実行して選択タブを維持
- `web/templates/base.html` の JS バージョンを更新してキャッシュ影響を回避
- `web/routes.py` と `web/templates/components/ng_dates_form.html` を更新し、各NG操作で `active_tab` を送信・再描画時に同タブをサーバー側で復元する方式へ変更（クライアント依存を排除）

### 変更ファイル

- `web/templates/components/ng_dates_form.html`
- `web/static/js/app.js`
- `web/templates/base.html`
- `web/routes.py`

---

## 2026-02-06: 結果画面に設定NGデータを常時表示

### 変更内容

- `src/ng_status_view.py` を拡張し、担当者に未割当のNGでも日付/週に設定NGがあれば `設定NG` ラベルを表示するよう変更
- これにより、スケジュールが制約を満たして担当者NGが0件でも「その日に登録されているNG設定」を結果画面で確認可能に改善
- `web/static/css/style.css` に `設定NG` チップ (`.ng-chip-setting`) のスタイルを追加
- `tests/test_ng_status_view.py` に、非担当者NGを表示する回帰テストを追加

### 変更ファイル

- `src/ng_status_view.py`
- `web/static/css/style.css`
- `tests/test_ng_status_view.py`

### テスト

- `py -3 -m pytest tests/test_ng_status_view.py -q`（5 passed）
- `py -3 -m pytest -q`（既存テスト1件失敗: `tests/test_schedule_builder.py::test_calculate_priority_score_no_history`）

---

## 2026-02-06: NG日程サブタブの選択状態を保持

### 変更内容

- `web/templates/components/ng_dates_form.html` のサブタブに `data-ng-tab` を追加
- タブ切替ロジックを `sessionStorage` ベースに変更し、HTMX再描画後も直前に開いていたサブタブを復元
- NG追加/削除/一括登録/詳細編集の実行後に、先頭タブへ戻らず同じタブを維持するよう改善

### 変更ファイル

- `web/templates/components/ng_dates_form.html`

---

## 2026-02-06: NG一括登録の日付年判定を改善（年未指定・年跨ぎ対応）

### 変更内容

- `src/ng_text_parser.py` の年解釈を「年度固定」から「基準年 + 年跨ぎ自動判定」に変更
- 年未指定 (`M/D`) は基準年で解釈し、`12月→1月` などの遷移を入力順から翌年へ自動繰り上げ
- `2/23,3/2,4/20` のような並びは同一年として扱い、意図しない `2026/2027` 混在を防止
- `YYYY/M/D` の明示年入力に対応し、同一行内の月省略（例: `2026/12/28,29`）も展開可能に
- 基準年選択UIの文言を `年度` から `基準年` に変更し、年跨ぎルールの説明を追加

### 変更ファイル

- `src/ng_text_parser.py`
- `tests/test_ng_text_parser.py`
- `web/templates/components/ng_dates_form.html`

### テスト

- `py -3 -m pytest tests/test_ng_text_parser.py -q`（54 passed）
- `py -3 -m pytest -q`（既存テスト1件失敗: `tests/test_schedule_builder.py::test_calculate_priority_score_no_history`）

---

## 2026-02-06: 結果画面のNG可視化UIを強化

### 変更内容

- 結果表示用に `src/ng_status_view.py` を追加し、日勤（日付単位）/夜勤（週単位）の `global`・`by_member`・`by_period` NG情報を行単位で集約
- `web/services.py` のスケジュール生成結果に `ng_status` を付与し、テンプレート側でNG情報を直接参照可能に変更
- `web/templates/components/schedule_variant.html` に `NG確認` 列を追加し、各行でNG種別（全体NG/個別NG/期間NG）をチップ表示
- 同テンプレートに `全件 / NGありのみ` フィルタとNG確認サマリーを追加し、確認作業を短縮
- `web/static/css/style.css` と `web/static/js/app.js` に、NG行ハイライトとフィルタ動作用のスタイル/スクリプトを追加
- ブラウザキャッシュ対策として `web/templates/base.html` の静的アセットバージョンを更新

### 変更ファイル

- `src/ng_status_view.py`
- `web/services.py`
- `web/templates/components/schedule_variant.html`
- `web/static/css/style.css`
- `web/static/js/app.js`
- `web/templates/base.html`
- `tests/test_ng_status_view.py`

### テスト

- `py -3 -m pytest tests/test_ng_status_view.py -q`（3 passed）
- `py -3 -m pytest -q`（既存テスト1件失敗: `tests/test_schedule_builder.py::test_calculate_priority_score_no_history`）

---

## 2026-02-06: EXE起動時のタスクバーアイコン反映を強化

### 変更内容

- `web/app.py` に Windows 向け `AppUserModelID` 設定を追加し、タスクバー表示アイコンの安定性を向上
- `pywebview` ウィンドウ表示後に `auto_arranger.ico` を `WM_SETICON` で適用する処理を追加
- リソース参照を `sys._MEIPASS` / ソース実行の双方で解決できるように整理
- `build_exe.py` のアイコンパス解決をプロジェクトルート基準に統一し、`--icon` 指定を明確化

### 変更ファイル

- `web/app.py`
- `build_exe.py`

---

## 2026-02-06: NG一括登録の名前/依頼日ずれ修正

### 変更内容

- `src/ng_text_parser.py` の一括テキスト分割処理を修正し、`名前` / `依頼日` のラベル付き入力を正規化して正しく解釈するように変更
- `名前` 行・`依頼日` 行の単独ラベル形式（複数行）と `名前: 値` / `依頼日: 値` 形式（1行）の双方に対応
- `日付` 行の直下に複数の `名前` 行が続く入力（1日付に複数名）を正しく展開するように変更
- 一括登録フォームの案内文とプレースホルダを `日付→名前` 優先に更新し、入力フォーマットの誤解を防止

### 変更ファイル

- `src/ng_text_parser.py`
- `tests/test_ng_text_parser.py`
- `web/templates/components/ng_dates_form.html`

### テスト

- `py -3 -m pytest tests/test_ng_text_parser.py -q`（47 passed）

---

## 2026-01-26: 2025-08-21〜2026-02-22 当番データ追記

### 変更内容

- 画像の当番表を基に `data/duty_roster_2021_2025.csv` に夜勤・休日当番を追記
- 2025-08-21 から 2026-02-22 までの夜勤（Night 1/2）と休日当番（Day 1/2/3）を追加

### 変更ファイル

- `data/duty_roster_2021_2025.csv`

## 2025-12-26: バリアント出力機能の追加

### 追加機能

- **複数バージョン生成**: `--variants` で同一設定から複数の当番表を生成・表示可能に。
- **上位候補からの分岐**: `--variant-top-k` により、各枠の上位k候補からバリアントごとに安定的に選択。
- **CSV出力の自動分割**: バリアント数が複数の場合、`_v1` などのサフィックス付きで出力。

### 変更ファイル

- `src/schedule_builder.py`: バリアント選択ロジック追加
- `main.py`: CLI引数追加と複数出力対応
- `README.md`: 使用例の追加
- `web/services.py`: バリアント生成API対応
- `web/routes.py`: UI生成・保存のバリアント対応
- `web/templates/components/schedule_result.html`: バリアント切替UI
- `web/templates/components/schedule_variant.html`: バージョン別表示
- `web/templates/index.html`: 生成オプション追加
- `web/static/js/app.js`: バリアント切替ロジック
- `web/static/css/style.css`: バリアントUIスタイル

---

## 2025-12-25: システム完成・運用フロー確立

### 実装完了

- **Greedyアルゴリズム採用**: PuLP（数理最適化）の代わりに、優先度スコアと制約チェックによるGreedyアルゴリズムを実装。計算速度と実装の柔軟性を優先。
- **主要モジュール**:
  - `src/schedule_builder.py`: スケジュール構築ロジック
  - `src/constraint_checker.py`: 制約チェックロジック
  - `src/output_formatter.py`: 結果出力・統計表示
  - `main.py`: CLIエントリーポイント

### 機能追加・変更

- **エラーハンドリング**: 候補者が見つからない場合、制約チェック結果（NG理由）を詳細に表示して停止する仕様に確定。
- **運用フロー定義**:
  - NG日: `config/ng_dates.yaml` (日付/期間/Global)
  - 免除: `config/settings.yaml` (`active: false`)
  - 履歴更新: 確定データを `data/duty_roster_2021_2025.csv` に追記する運用ルールを策定。

---

## 2025-12-24: プロジェクト初期構築

### Phase 1: 基盤構築完了

#### 追加ファイル

- `requirements.txt`: 依存ライブラリ定義
  - pandas, PuLP, PyYAML, tabulate, python-dateutil, pytest
- `utils/logger.py`: ログ設定モジュール
  - コンソール・ファイル出力対応
  - ログレベル設定機能
- `utils/date_utils.py`: 日付処理ユーティリティ
  - ローテーション期間計算
  - 週の範囲計算（月曜～日曜）
  - 期間内の月曜日・土日取得
  - 過去期間計算
- `src/data_loader.py`: CSVデータ読み込み・前処理
  - CSV読み込み機能
  - 重複行除去（179行削除）
  - 欠損値・変更マーカー除外（3行削除）
  - 直近N ヶ月のデータ抽出
  - メンバー履歴分析

#### データ処理結果

- **元データ**: 3,501レコード
- **クリーニング後**: 3,319レコード
- **直近2ヶ月**: 142レコード
- **アクティブメンバー**: 22名

---

### Phase 2: 設定管理完了

#### 追加ファイル

- `src/config_generator.py`: 設定ファイル自動生成モジュール
  - 過去2ヶ月のデータからメンバー分類
  - settings.yaml自動生成
  - ng_dates.yaml雛形生成
- `config/settings.yaml`: メンバー・制約設定（自動生成）
  - 日勤 index 1,2グループ: 16名
  - 日勤 index 3グループ: 5名
  - 夜勤 index 1グループ: 9名
  - 夜勤 index 2グループ: 5名（松田さん含む）
  - 松田さん隔週パターン設定（基準日: 2025-02-20）
- `config/ng_dates.yaml`: NG日設定雛形

#### メンバー分類ロジック

過去2ヶ月の実績データから以下の基準で自動分類:

- 日勤でindex 1または2に出現 → `day_shift.index_1_2_group`
- 日勤でindex 3に出現 → `day_shift.index_3_group`
- 夜勤でindex 1に出現 → `night_shift.index_1_group`
- 夜勤でindex 2に出現 → `night_shift.index_2_group`

#### 松田さん特別設定

- 夜勤 index 2に固定
- 隔週パターン（biweekly）
- 基準日を過去データから自動検出: 2025-02-20

---

### テスト実装完了

#### 追加ファイル

- `tests/test_date_utils.py`: 日付ユーティリティテスト（7テスト）
- `tests/test_data_loader.py`: データローダーテスト（6テスト）
- `tests/test_config_generator.py`: 設定生成テスト（5テスト）

#### テスト結果

- **合計**: 18テスト
- **成功**: 18テスト（100%）
- **失敗**: 0テスト

#### テスト検証項目

1. **日付処理**:
   - ローテーション期間計算（21日～2ヶ月後の20日）
   - 週の範囲計算（月曜～日曜）
   - 土日判定
2. **データ処理**:
   - CSV読み込み
   - 重複除去・欠損値除外
   - メンバー履歴分析
3. **設定生成**:
   - メンバー分類の正確性
   - 松田さんの設定
   - YAML保存・読み込み

---

### ドキュメント整備

#### 追加ファイル

- `.docs/CLAUDE.md`: プロジェクト説明書
  - プロジェクト概要
  - 技術スタック
  - 制約ルール詳細
  - データ分析結果
  - 使用方法
  - 実装状況
- `.docs/update.md`: このファイル
- `README.md`: プロジェクト概要（作成予定）

---

### データファイル移動

- `duty_roster_2021_2025.csv` をプロジェクトルートから `data/` ディレクトリに移動

---

### 技術的な決定事項

#### 設定ファイル管理方針

- **初回起動時**: 過去データから自動生成
- **2回目以降**: 既存ファイルを使用（手動編集可能）
- **理由**: 初期設定の手間を省きつつ、運用中の柔軟性を確保

#### メンバー分類基準

- **期間**: 直近2ヶ月
- **判定**: 過去の実績から自動分類
- **根拠**: ユーザー要件「直近2か月でindex 1,2に該当した人は3にはできない」

#### 松田さん隔週パターン

- **検出方法**: 過去データの最終出現日から計算
- **設定**: 夜勤 index 2固定、隔週パターン
- **根拠**: 過去データで376回出現、すべて夜勤 index 2
