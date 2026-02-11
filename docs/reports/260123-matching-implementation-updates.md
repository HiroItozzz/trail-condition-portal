# レコード照合機能の実装と改善

## 更新日
2026-01-12

## 概要

登山道状況データのレコード照合ロジックをRapidFuzzベースに全面改修し、テストコマンドと重複検出機能を追加しました。

## 主な変更内容

### 1. RapidFuzzベースの3段階照合アルゴリズム実装

**対象ファイル**: `trail_status/services/db_writer.py`

**詳細ドキュメント**: `documents/record-matching-algorithm.md`

#### 実装内容（サマリー）

- 完全一致 → 類似度マッチ（RapidFuzz） → 新規作成の3段階アルゴリズム
- 複数フィールドの複合スコアリング（山名、登山道名、タイトル、説明）
- ボーナススコア（status一致、日付近接）
- 調整可能なクラス定数（閾値、重み、ボーナス値など）

詳細は[レコード同定アルゴリズム](./record-matching-algorithm.md)を参照。

---

### 2. fetcher.pyのリファクタリング

**対象ファイル**: `trail_status/services/fetcher.py`

#### 変更内容

重複していた`trafilatura.extract()`呼び出しを共通メソッドに統合しました。

#### 新規メソッド

```python
def _extract_content(self, html: str, include_links: bool = False,
                     include_comments: bool = False) -> str:
    """
    TrafilaturaでHTMLからコンテンツを抽出（共通処理）

    Args:
        include_links: リンク情報を含めるか
            - True: AI用テキスト（reference_URL抽出のため）
            - False: ハッシュ計算用（URL変更を無視）
    """
```

#### 使用箇所

- `fetch_parsed_text()`: `include_links=True`でAI用テキストを生成
- `calculate_content_hash()`: `include_links=False`でハッシュ計算（URL変更による誤検知を防止）

---

### 3. test_matchingコマンドの新規作成

**対象ファイル**: `trail_status/management/commands/test_matching.py`

#### 目的

RapidFuzz照合ロジックをDB保存なしでテストするための専用コマンド。

#### 機能

1. **単一情報源モード**（`--source`指定時）
   - 指定した情報源のみ処理
   - 最新サンプルJSONを対話的に選択
   - 各レコードの照合詳細を表示（更新対象・新規作成）

2. **全情報源一括モード**（引数なし）
   - `trail_status/services/sample/`配下の全ディレクトリをスキャン
   - 各情報源の最新JSONファイルを自動選択
   - 全体のサマリーを表示

#### 使い方

```bash
# 全情報源を一括テスト
docker compose exec web uv run manage.py test_matching

# 特定の情報源のみテスト（詳細表示）
docker compose exec web uv run manage.py test_matching --source 1

# 特定のファイルを指定
docker compose exec web uv run manage.py test_matching --source 1 --json-file path/to/sample.json
```

#### 出力例（全情報源モード）

```
======================================================================
全情報源 照合結果サマリー
======================================================================

✅ 奥多摩ビジターセンター (gpt-5-mini_20260112_152123.json)
   更新: 45件 / 新規: 5件 / 合計: 50件

✅ 御岳ビジターセンター (deepseek-chat_20260112_150344.json)
   更新: 12件 / 新規: 2件 / 合計: 14件

======================================================================
総合計: 更新 57件 / 新規 7件 / 全レコード 64件
処理した情報源: 2件
======================================================================
```

---

### 4. 重複照合エラーハンドリングの追加

**対象ファイル**: `trail_status/services/db_writer.py`

#### 実装内容

同じ既存レコードに複数のAIデータが照合されるのを検出・防止する機能を追加しました。

#### 仕組み

```python
matched_record_ids: set[int] = set()  # 照合済みレコードIDを追跡

# 照合成功時
if existing_record.id in matched_record_ids:
    # 重複検出 → ValueError を投げて処理を停止
    raise ValueError(...)

matched_record_ids.add(existing_record.id)
```

#### エラー時の出力

```
ERROR 重複照合エラー: レコードID 123 が複数のAIデータと照合されました
  既存: 雲取山/鴨沢ルート
  新規: 雲取山/鴨沢登山口ルート

ValueError: 重複照合エラー: 同じ既存レコード（ID: 123）に複数のAIデータが照合されました。
AIが同一の登山道情報を重複抽出している可能性があります。
```

#### 想定される重複原因

1. **AIの重複抽出**: 同じ情報源から同じ登山道を2回抽出
2. **表記ゆれによる誤照合**: 類似度閾値が低すぎて異なる登山道が同一レコードに照合

#### 対処方法

- エラー発生時はAI出力を確認
- プロンプトの改善または閾値の調整

---

## 依存関係の変更

**追加されたパッケージ**: `rapidfuzz`

```bash
uv add rapidfuzz
```

---

## 関連ドキュメント

- [レコード同定アルゴリズム詳細](./record-matching-algorithm.md) - RapidFuzzアルゴリズムの完全な仕様
- [CLAUDE.md](../.claude/CLAUDE.md) - プロジェクト全体の概要と共通コマンド

---

## テスト方法

### 1. 照合ロジックのテスト

```bash
# 全情報源の照合結果を確認
docker compose exec web uv run manage.py test_matching

# 特定情報源の詳細を確認
docker compose exec web uv run manage.py test_matching --source 1
```

### 2. 実際のDB保存テスト

```bash
# DRY-RUNモード（照合のみ、DB保存なし）
docker compose exec web uv run manage.py trail_sync --source 1 --dry-run

# 本番実行
docker compose exec web uv run manage.py trail_sync --source 1
```

---

## 今後の改善案

### 短期

- 照合ログの詳細化（類似度スコアの内訳を出力）
- test_matchingコマンドにスコア詳細表示オプション追加

### 中期

- 閾値の自動チューニング機能
- 照合失敗ケースの自動収集と分析

### 長期

- スコア 0.6-0.7 の微妙なケースにAI判定を追加
- 機械学習による最適重みの自動調整

詳細は[レコード同定アルゴリズム](./record-matching-algorithm.md#将来の改善案)を参照。

---

## 重複照合問題の解決方針（実装予定）

### 問題

現在の実装では、AIデータを順番に処理するため、後のデータが既に照合済みのレコードに誤って照合されると重複エラーが発生する。

### 解決策: 類似度順マッチングアルゴリズム

**対象ファイル**: `trail_status/services/db_writer.py`
**修正メソッド**: `_reconcile_records()`

#### 実装方針

1. **全組み合わせのスコア計算**
   ```python
   # 全ての(AIデータ × 既存レコード)の組み合わせで類似度を計算
   matches = []
   for ai_data in ai_data_list:
       for candidate in candidates:
           score = self._calculate_similarity(candidate, ai_data)
           if score >= self.SIMILARITY_THRESHOLD:
               matches.append((score, candidate, ai_data))
   ```

2. **スコアで降順ソート**
   ```python
   # 類似度の高い順に並べる
   matches.sort(key=lambda x: x[0], reverse=True)
   ```

3. **グリーディに割り当て**
   ```python
   used_records = set()
   used_ai_data = set()

   for score, record, ai_data in matches:
       # 既に使われていたらスキップ
       if record.id in used_records or id(ai_data) in used_ai_data:
           continue

       # 照合確定
       used_records.add(record.id)
       used_ai_data.add(id(ai_data))

       # 更新リストに追加
       ...
   ```

4. **未照合のAIデータは新規作成**
   ```python
   for ai_data in ai_data_list:
       if id(ai_data) not in used_ai_data:
           to_create.append(...)
   ```

#### メリット

- **重複照合が自然に解消**: 最もスコアの高い組み合わせが優先される
- **グローバル最適**: 各AIデータが最も適切な既存レコードに照合される
- **実装が明確**: ソート後に順番に処理するだけ

#### 注意点

- **計算量**: O(N × M)（N=AIデータ数、M=既存レコード数）
  - 現在: 最大50レコード程度 → 2500回の類似度計算（問題なし）
- **完全一致の優先**: スコア1.0（完全一致）が最優先される
- **メモリ**: 全組み合わせを一時保持（50×50×16B = 約40KB、問題なし）

#### 実装タイミング

重複照合の発生頻度を確認後、必要に応じて実装。現在の警告ベースの対応で十分な場合は保留。
