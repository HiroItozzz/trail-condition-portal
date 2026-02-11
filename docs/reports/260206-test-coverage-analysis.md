# テストカバレッジ分析・改善提案

**作成日**: 2026-02-06
**分析対象**: trail-condition-portal プロジェクト
**現在のテスト数**: 19テスト（全てパス）

---

## 📊 現在のテスト状況

### ✅ テスト済みコンポーネント（19テスト）

| カテゴリ | ファイル | カバー内容 | テスト数 |
|---------|---------|-----------|----------|
| 設定 | `test_config_files.py` | プロンプトファイル読み込み、AI設定 | 3 |
| フェッチャー | `test_fetcher.py` | HTML解析、ハッシュ計算、変更検知 | 3 |
| LLMクライアント | `test_llm_clients.py` | DeepSeek初期化、プロンプト生成、API呼び出し | 3 |
| LLM設定 | `test_llm_config.py` | 設定検証、APIキー検出、温度範囲 | 6 |
| パイプライン | `test_pipeline.py` | 全体フロー（モック使用） | 1 |
| スキーマ | `test_schema_validation.py` | Pydanticスキーマ検証 | 3 |

**合計**: 19テスト

---

## ⚠️ テストが不足しているコンポーネント

### 🚨 Critical（最重要・優先度1）

#### 1. `services/db_writer.py` - レコード同定アルゴリズム

- **行数**: 約450行
- **重要度**: ⭐⭐⭐⭐⭐（プロジェクトの核心）
- **現状**: 管理コマンド `test_matching.py` で手動テストのみ
- **カバレッジ推定**: 0%

**不足しているテスト**:
```python
# 必要なテストケース
- test_reconcile_records_exact_match()      # 完全一致
- test_reconcile_records_similarity_match() # 類似度マッチング（閾値0.7）
- test_reconcile_records_new_creation()     # 新規作成判定
- test_calculate_similarity_score()         # 類似度計算ロジック
- test_decompose_text_with_sudachipy()      # SudachiPy形態素解析
- test_normalize_text()                     # テキスト正規化
- test_edge_cases_empty_description()       # エッジケース: 空の説明文
- test_edge_cases_similar_mountains()       # エッジケース: 類似山名
- test_threshold_boundary_0_69()            # 閾値境界: 0.69 → 新規
- test_threshold_boundary_0_70()            # 閾値境界: 0.70 → 更新
- test_threshold_boundary_0_71()            # 閾値境界: 0.71 → 更新
- test_field_weights_with_description()     # 重み付け: description有り
- test_field_weights_without_description()  # 重み付け: description無し
```

**なぜ重要？**:
- **名寄せ精度99%を達成している中核ロジック**
- RapidFuzz + SudachiPyの統合部分
- バグがあると重複レコードや誤同定が発生
- 本番データの品質を直接左右する

**推定作業量**: 4-6時間

---

#### 2. `views.py` - Webビュー

- **行数**: 約150行
- **重要度**: ⭐⭐⭐⭐（ユーザー体験の入口）
- **現状**: テストゼロ
- **カバレッジ推定**: 0%

**不足しているテスト**:
```python
# ビュー関数
- test_trail_list_view_success()            # 一覧表示（200 OK）
- test_trail_list_with_source_filter()      # フィルタ: 情報源
- test_trail_list_with_area_filter()        # フィルタ: 山域
- test_trail_list_with_status_filter()      # フィルタ: 状況種別
- test_trail_list_multiple_filters()        # 複数フィルタ組み合わせ
- test_trail_detail_view_success()          # 詳細表示（200 OK）
- test_trail_detail_not_found()             # 詳細表示（404 Not Found）
- test_about_page()                         # aboutページ
- test_site_policy_page()                   # サイトポリシーページ

# ヘルパー関数
- test_sidebar_context_generation()         # サイドバーコンテキスト
- test_sidebar_counts_accuracy()            # 件数カウント正確性
- test_recent_sources_limit()               # 最近の情報源（最新5件）
- test_canonical_url_generation()           # SEO: canonical URL
```

**なぜ重要？**:
- ユーザーが直接触れる部分
- フィルタリングロジックのバグは即座にUX低下
- SEO関連機能（canonical URL）の動作保証

**推定作業量**: 2-3時間

---

### ⚠️ High（高優先度・優先度2）

#### 3. `models/` - Djangoモデル

- **ファイル**: `condition.py`, `mountain.py`, `source.py`, `llm_usage.py`
- **行数**: 約220行（合計）
- **重要度**: ⭐⭐⭐⭐
- **現状**: テストゼロ
- **カバレッジ推定**: 0%

**不足しているテスト**:
```python
# TrailCondition モデル
- test_trail_condition_creation()           # モデル作成
- test_trail_condition_str_representation() # __str__メソッド
- test_trail_condition_get_absolute_url()   # URL生成
- test_trail_condition_ordering()           # デフォルトソート順
- test_trail_condition_disabled_flag()      # 無効化フラグ

# MountainGroup, AreaName モデル
- test_area_name_choices()                  # 山域選択肢
- test_area_name_get_yamareco_area_id()     # ヤマレコAPI連携（重要）
- test_mountain_group_str()                 # 山群表示

# DataSource モデル
- test_data_source_prompt_filename()        # プロンプトファイル名生成
- test_data_source_content_hash_update()    # ハッシュ更新
- test_data_source_last_checked_at()        # 最終チェック日時

# LlmUsage モデル
- test_llm_usage_cost_calculation()         # コスト記録
```

**なぜ重要？**:
- データ層の整合性保証
- 特に `get_yamareco_area_id()` はヤマレコAPI連携の基盤
- モデルのバグはマイグレーションで修正困難

**推定作業量**: 2時間

---

#### 4. `services/llm_stats.py` - LLMコスト計算

- **行数**: 約180行
- **重要度**: ⭐⭐⭐
- **現状**: テストゼロ
- **カバレッジ推定**: 0%

**不足しているテスト**:
```python
- test_llm_stats_token_calculation()        # トークン数計算
- test_llm_stats_cost_calculation_gemini()  # コスト: Gemini
- test_llm_stats_cost_calculation_deepseek() # コスト: DeepSeek
- test_llm_stats_cost_calculation_gpt()     # コスト: GPT
- test_llm_stats_to_dict()                  # 辞書変換
- test_llm_stats_total_fee()                # 合計コスト
```

**なぜ重要？**:
- LLMコスト最適化（月間1/10削減）の正確性保証
- コスト計算ミスは予算に直結

**推定作業量**: 1-2時間

---

#### 5. 管理コマンド

- **ファイル**: `trail_sync.py`, `test_llm.py`, `backup_db.py`
- **行数**: 約350行（合計）
- **重要度**: ⭐⭐⭐
- **現状**: `test_matching.py` は手動テストツール（pytestスイート外）
- **カバレッジ推定**: 0%

**不足しているテスト**:
```python
# trail_sync.py
- test_trail_sync_command_basic()           # 基本実行
- test_trail_sync_with_source_filter()      # --source オプション
- test_trail_sync_dry_run()                 # --dry-run オプション
- test_trail_sync_with_model()              # --model オプション
- test_trail_sync_new_hash_flag()           # --new-hash オプション

# test_llm.py
- test_test_llm_command()                   # LLM接続テスト
```

**なぜ重要？**:
- バッチ処理の信頼性
- 本番環境での定期実行コマンド

**推定作業量**: 2-3時間

---

### 📊 Medium（中優先度・優先度3）

#### 6. `services/slack_notifier.py`

- **行数**: 約100行
- **重要度**: ⭐⭐
- **現状**: テストゼロ
- **影響範囲**: 通知機能のみ（本番への直接影響は小）

**推定作業量**: 1時間

---

#### 7. 統合テスト（Integration Tests）

- **現状**: 単体テスト（Unit Tests）が中心
- **不足**: E2Eテスト（フェッチ→AI処理→DB保存の一連の流れ）

**不足しているテスト**:
```python
- test_end_to_end_pipeline()                # E2E: 全パイプライン
- test_integration_fetch_to_db()            # 統合: フェッチ→DB
- test_integration_llm_to_matching()        # 統合: LLM→名寄せ
```

**推定作業量**: 3-4時間

---

## 📈 テストカバレッジの推定

### 現状のカバレッジ（推定）

```
全体推定カバレッジ: 約40-50%
目標カバレッジ: 70-80%

【カバー済み】
✅ fetcher.py          → 80%
✅ llm_client.py       → 60%
✅ pipeline.py         → 50% (モックが多い)
✅ schema.py           → 90%
✅ 設定ファイル         → 80%

【未カバー】
❌ db_writer.py        → 0%  ← 最重要！
❌ views.py            → 0%
❌ models/             → 0%
❌ llm_stats.py        → 0%
❌ 管理コマンド         → 0%
❌ slack_notifier.py   → 0%
```

### コンポーネント別カバレッジ目標

| コンポーネント | 現在 | 目標 | 優先度 |
|--------------|------|------|--------|
| db_writer.py | 0% | 80% | Critical |
| views.py | 0% | 70% | Critical |
| models/ | 0% | 60% | High |
| llm_stats.py | 0% | 70% | High |
| 管理コマンド | 0% | 50% | High |
| pipeline.py | 50% | 70% | Medium |
| llm_client.py | 60% | 80% | Medium |

---

## 🧪 テスト実装時の注意点

### 工夫が必要な箇所と対策

#### 1. 🚨 DbWriter.sudachi がクラス変数で初期化（影響度: ⭐⭐⭐）

**問題のコード**:
```python
class DbWriter:
    # クラスロード時に1回だけ実行される
    sudachi = Dictionary(dict="core").create()  # ← これ！
```

**問題点**:
- テスト時に SudachiPy をモック化できない
- Dictionary の初期化に時間がかかる（テスト実行が遅くなる）
- 実際の SudachiPy を使うため、テストが環境依存

**対策**:
```python
# Option A: ファクトリメソッドで注入可能にする（リファクタリング必要）
class DbWriter:
    def __init__(self, ..., sudachi=None):
        self.sudachi = sudachi or Dictionary(dict="core").create()

# Option B: そのまま実SudachiPyを使ってテスト（推奨）
# （動作は遅いがテストの正確性は高い）
```

---

#### 2. 🚨 DbWriter.__init__ の依存が重い（影響度: ⭐⭐⭐⭐）

**問題のコード**:
```python
def __init__(
    self,
    source_schema_single: SourceSchemaSingle,  # 複雑
    result_by_source: ResultSingle | BaseException,  # 複雑
):
```

**問題点**:
- `SourceSchemaSingle` と `ResultSingle` という複雑なオブジェクトが必須
- これらを用意するのに手間がかかる
- テストコードが冗長になりがち

**対策**:
```python
# テスト用ファクトリ関数を作る
@pytest.fixture
def db_writer_factory(db):
    def _create(
        source_id=1,
        trail_data=None,
        **kwargs
    ):
        source_schema = SourceSchemaSingle(
            id=source_id,
            name="テスト",
            url1="https://test.com",
            prompt_key="test",
            content_hash=None,
        )
        result = ResultSingle(
            success=True,
            content_changed=True,
            extracted_trail_conditions=TrailConditionSchemaList(...),
            config=LlmConfig(...),
            stats=LlmStats(...),
            new_hash="abc123",
        )
        return DbWriter(source_schema, result)
    return _create

# 使う時
def test_something(db_writer_factory):
    writer = db_writer_factory(source_id=1)
    ...
```

---

#### 3. ⚠️ source_record プロパティがDB直アクセス（影響度: ⭐⭐⭐）

**問題のコード**:
```python
@property
def source_record(self) -> DataSource:
    return DataSource.objects.get(id=self.source_schema_single.id)  # 毎回DBクエリ
```

**問題点**:
- プロパティアクセスのたびに DB クエリ実行
- テストでは必ず DB フィクスチャが必要
- モック化が難しい

**現状の評価**:
- Django のテストでは `@pytest.mark.django_db` があるので**許容範囲**
- 実際のDBを使うことで統合テストになり、正確性が高まる

---

#### 4. 🚨 reconcile_records が複雑すぎる（影響度: ⭐⭐⭐⭐⭐ 最高）

**問題のコード**:
```python
def reconcile_records(
    self, ai_record_list: list[TrailConditionSchemaInternal]
) -> tuple[list[TrailCondition], list[TrailCondition]]:
    # 1. DB クエリでレコード取得
    # 2. 類似度計算（総当たり）
    # 3. マッチング判定
    # 4. 新規/更新の振り分け
    # 5. ログ出力
    # ... 約120行
```

**問題点**:
- 1つのメソッドが多責任（単一責任原則違反）
- DB アクセス + ビジネスロジック + 類似度計算が混在
- テストケースが多数必要（複雑度が高い）
- モック化しづらい

**対策案（リファクタリング）**:
```python
# メソッドを分割する
def reconcile_records(self, ai_record_list):
    candidates = self._fetch_candidates()  # DB層
    matches = self._calculate_matches(candidates, ai_record_list)  # ロジック層
    return self._assign_records(matches, ai_record_list)  # ロジック層

# これなら各メソッドを個別にテスト可能
```

**現実的な対策（リファクタリングなし）**:
```python
# 統合テスト的アプローチで現状のまま
@pytest.mark.django_db
def test_reconcile_records_full_flow(db):
    # 実際のDBとSudachiPyを使って統合テスト
    # 遅いが正確
    ...
```

---

#### 5. ⚠️ decompose_text がインスタンスメソッド（影響度: ⭐⭐）

**問題のコード**:
```python
@lru_cache
def decompose_text(self, text: str, noun_only: bool = False) -> str:
    # self.sudachi に依存
    for m in self.sudachi.tokenize(normalized, self.SPLIT_MODE):
        ...
```

**問題点**:
- `self.sudachi` に依存するため `@staticmethod` にできない
- テスト時にインスタンスが必要

**現状の評価**:
- `@lru_cache` でキャッシュされているので許容範囲
- 実際の SudachiPy を使ってテストすれば問題なし

---

## 💡 テスト実装戦略

#### Option A: 現状の設計でテストを書く（推奨）

**アプローチ**: 統合テスト的に実際のDB + SudachiPyを使う

```python
@pytest.mark.django_db
class TestDbWriterReconcile:
    @pytest.fixture
    def sample_source(self, db):
        return DataSource.objects.create(...)

    @pytest.fixture
    def db_writer(self, sample_source):
        # 実際のオブジェクトを用意
        source_schema = SourceSchemaSingle(
            id=sample_source.id,
            name="テスト",
            url1="https://test.com",
            prompt_key="test",
            content_hash=None,
        )
        result = ResultSingle(
            success=True,
            content_changed=True,
            extracted_trail_conditions=TrailConditionSchemaList(...),
            config=LlmConfig(...),
            stats=LlmStats(...),
            new_hash="abc123",
        )
        return DbWriter(source_schema, result)

    def test_reconcile_exact_match(self, db_writer, sample_source):
        # 既存レコード作成
        existing = TrailCondition.objects.create(...)

        # AI出力データ
        ai_data = TrailConditionSchemaInternal(...)

        # 実行
        to_update, to_create = db_writer.reconcile_records([ai_data])

        # 検証
        assert len(to_update) == 1
        assert len(to_create) == 0
```

**メリット**:
- ✅ コードを変更しなくていい
- ✅ 実際の動作をテストできる
- ✅ SudachiPy も本物を使うので正確

**デメリット**:
- ⚠️ テスト実行が遅い
- ⚠️ セットアップが複雑

---

#### Option B: リファクタリングしてからテストを書く

**アプローチ**: `reconcile_records` を分割して純粋関数化

```python
class DbWriter:
    def reconcile_records(self, ai_record_list):
        candidates = self._fetch_candidates()
        matches = self._calculate_matches(candidates, ai_record_list)
        return self._assign_records(matches, ai_record_list)

    def _fetch_candidates(self):
        """DB層 - モック可能"""
        return list(TrailCondition.objects.filter(...))

    def _calculate_matches(self, candidates, ai_record_list):
        """ロジック層 - 純粋関数的、テストしやすい"""
        matches = []
        for ai_record in ai_record_list:
            for candidate in candidates:
                score = self._calculate_similarity(candidate, ai_record)
                if score >= self.SIMILARITY_THRESHOLD:
                    matches.append((score, candidate, ai_record))
        return sorted(matches, key=lambda x: x[0], reverse=True)

    def _assign_records(self, matches, ai_record_list):
        """ロジック層 - 純粋関数的、テストしやすい"""
        ...
```

**メリット**:
- ✅ 各メソッドを個別にテスト可能
- ✅ モック化しやすい
- ✅ テストが高速

**デメリット**:
- ⚠️ リファクタリングが必要
- ⚠️ 既存の動作を壊すリスク

**推奨**: まずは Option A で実装し、遅くなったら Option B を検討

---

## 🎯 推奨実装計画

### Phase 1: Critical（必須・優先度1）

#### 1️⃣ `test_db_writer.py` 作成

**新規ファイル**: `trail_status/tests/test_db_writer.py`

**推定作業量**: 4-6時間
**推定テスト数**: 15-20個

**実装すべきテスト**:
```python
import pytest
from trail_status.services.db_writer import DbWriter
from trail_status.models.condition import TrailCondition
from trail_status.services.schema import TrailConditionSchemaInternal

class TestDbWriter:
    """DbWriterクラスの基本テスト"""

    def test_normalize_text_basic(self):
        """テキスト正規化の基本動作"""
        result = DbWriter.normalize_text("　全角スペース　")
        assert result == "全角スペース"

    def test_decompose_text_with_sudachipy(self):
        """SudachiPyによる形態素解析"""
        db_writer = DbWriter(source_schema_single=..., result=...)
        result = db_writer.decompose_text("雲取山登山道")
        # トークン分割の検証
        assert "雲取山" in result
        assert "登山道" in result


class TestRecordMatching:
    """レコード同定アルゴリズムのテスト"""

    @pytest.fixture
    def existing_record(self, db):
        """テスト用の既存レコード"""
        return TrailCondition.objects.create(
            trail_name="雲取山登山道",
            mountain_name_raw="雲取山",
            title="通行止め",
            description="土砂崩れのため通行止め",
            status="CLOSURE",
            ...
        )

    def test_reconcile_exact_match(self, db, existing_record):
        """完全一致でレコードを同定"""
        ai_data = TrailConditionSchemaInternal(
            trail_name="雲取山登山道",
            mountain_name_raw="雲取山",
            title="通行止め",
            description="土砂崩れのため通行止め",
            status="CLOSURE",
            ...
        )

        db_writer = DbWriter(...)
        to_update, to_create = db_writer.reconcile_records([ai_data])

        assert len(to_update) == 1
        assert len(to_create) == 0
        assert to_update[0].id == existing_record.id

    def test_reconcile_similarity_match(self, db, existing_record):
        """類似度マッチング（閾値0.7超え）"""
        ai_data = TrailConditionSchemaInternal(
            trail_name="雲取山ルート",  # 微妙に違う
            mountain_name_raw="雲取",    # 微妙に違う
            title="通行不可",           # 微妙に違う
            description="土砂崩れで通行できません",
            status="CLOSURE",
            ...
        )

        db_writer = DbWriter(...)
        to_update, to_create = db_writer.reconcile_records([ai_data])

        # 類似度が閾値を超えるため、更新判定
        assert len(to_update) == 1
        assert len(to_create) == 0

    def test_reconcile_below_threshold_creates_new(self, db, existing_record):
        """類似度が閾値未満 → 新規作成"""
        ai_data = TrailConditionSchemaInternal(
            trail_name="大岳山登山道",  # 全く違う山
            mountain_name_raw="大岳山",
            title="通行可能",
            description="問題なし",
            status="CLEAR",
            ...
        )

        db_writer = DbWriter(...)
        to_update, to_create = db_writer.reconcile_records([ai_data])

        assert len(to_update) == 0
        assert len(to_create) == 1

    def test_threshold_boundary_0_69(self, db):
        """境界値: 類似度0.69 → 新規作成"""
        # 類似度が0.69になるようなデータを用意
        ...

    def test_threshold_boundary_0_70(self, db):
        """境界値: 類似度0.70（閾値）→ 更新"""
        # 類似度が0.70になるようなデータを用意
        ...

    def test_threshold_boundary_0_71(self, db):
        """境界値: 類似度0.71 → 更新"""
        ...


class TestSimilarityCalculation:
    """類似度計算ロジックのテスト"""

    def test_calculate_similarity_identical(self):
        """完全一致 → スコア1.0"""
        existing = TrailCondition(...)
        new_data = TrailConditionSchemaInternal(...)

        db_writer = DbWriter(...)
        score = db_writer._calculate_similarity(existing, new_data)

        assert score == 1.0

    def test_calculate_similarity_with_description(self):
        """description有りの場合の重み付け"""
        # FIELD_WEIGHT_MOUNTAIN = 0.2
        # FIELD_WEIGHT_TRAIL = 0.3
        # FIELD_WEIGHT_TITLE = 0.1
        # FIELD_WEIGHT_DESC = 0.4
        ...

    def test_calculate_similarity_without_description(self):
        """description無しの場合の重み付け"""
        # FIELD_WEIGHT_MOUNTAIN_NO_DESC = 0.2
        # FIELD_WEIGHT_TRAIL_NO_DESC = 0.4
        # FIELD_WEIGHT_TITLE_NO_DESC = 0.4
        ...


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_description(self, db):
        """説明文が空の場合"""
        ...

    def test_very_long_description(self, db):
        """説明文が非常に長い場合（DESC_COMPARE_LENGTH=200）"""
        ...

    def test_special_characters(self, db):
        """特殊文字が含まれる場合"""
        ...

    def test_similar_mountain_names(self, db):
        """類似山名の識別（雲取山 vs 雲取山南峰）"""
        ...
```

---

#### 2️⃣ `test_views.py` 作成

**新規ファイル**: `trail_status/tests/test_views.py`

**推定作業量**: 2-3時間
**推定テスト数**: 10-12個

**実装すべきテスト**:
```python
import pytest
from django.test import Client
from django.urls import reverse
from trail_status.models.condition import TrailCondition, AreaName, StatusType
from trail_status.models.source import DataSource

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def sample_data_source(db):
    return DataSource.objects.create(
        name="テスト情報源",
        url1="https://example.com",
    )

@pytest.fixture
def sample_trail_condition(db, sample_data_source):
    return TrailCondition.objects.create(
        source=sample_data_source,
        url1="https://example.com",
        trail_name="雲取山登山道",
        mountain_name_raw="雲取山",
        title="通行止め",
        description="土砂崩れ",
        status=StatusType.CLOSURE,
        area=AreaName.OKUTAMA,
        disabled=False,
    )


class TestTrailListView:
    """一覧ページのテスト"""

    def test_trail_list_success(self, client, sample_trail_condition):
        """一覧表示が正常に動作"""
        response = client.get(reverse('trail_list'))

        assert response.status_code == 200
        assert 'conditions' in response.context
        assert sample_trail_condition in response.context['conditions']

    def test_trail_list_with_source_filter(self, client, sample_trail_condition):
        """情報源フィルタが動作"""
        url = reverse('trail_list') + f'?source={sample_trail_condition.source.id}'
        response = client.get(url)

        assert response.status_code == 200
        assert len(response.context['conditions']) == 1

    def test_trail_list_with_area_filter(self, client, sample_trail_condition):
        """山域フィルタが動作"""
        url = reverse('trail_list') + f'?area={AreaName.OKUTAMA}'
        response = client.get(url)

        assert response.status_code == 200
        assert all(c.area == AreaName.OKUTAMA for c in response.context['conditions'])

    def test_trail_list_with_status_filter(self, client, sample_trail_condition):
        """状況種別フィルタが動作"""
        url = reverse('trail_list') + f'?status={StatusType.CLOSURE}'
        response = client.get(url)

        assert response.status_code == 200
        assert all(c.status == StatusType.CLOSURE for c in response.context['conditions'])

    def test_trail_list_excludes_disabled(self, client, sample_data_source):
        """disabled=Trueのレコードは表示しない"""
        TrailCondition.objects.create(
            source=sample_data_source,
            disabled=True,
            ...
        )

        response = client.get(reverse('trail_list'))
        assert len(response.context['conditions']) == 0


class TestTrailDetailView:
    """詳細ページのテスト"""

    def test_trail_detail_success(self, client, sample_trail_condition):
        """詳細表示が正常に動作"""
        url = reverse('trail_detail') + f'?id={sample_trail_condition.id}'
        response = client.get(url)

        assert response.status_code == 200
        assert 'condition' in response.context
        assert response.context['condition'].id == sample_trail_condition.id

    def test_trail_detail_not_found(self, client):
        """存在しないIDは404"""
        url = reverse('trail_detail') + '?id=99999'
        response = client.get(url)

        assert response.status_code == 404

    def test_trail_detail_disabled_returns_404(self, client, sample_trail_condition):
        """disabled=Trueは404"""
        sample_trail_condition.disabled = True
        sample_trail_condition.save()

        url = reverse('trail_detail') + f'?id={sample_trail_condition.id}'
        response = client.get(url)

        assert response.status_code == 404


class TestOtherPages:
    """その他のページのテスト"""

    def test_about_page(self, client):
        """aboutページ"""
        response = client.get(reverse('about'))
        assert response.status_code == 200

    def test_site_policy_page(self, client):
        """サイトポリシーページ"""
        response = client.get(reverse('site_policy'))
        assert response.status_code == 200


class TestSidebarContext:
    """サイドバーコンテキストのテスト"""

    def test_sidebar_context_structure(self, client, sample_trail_condition):
        """サイドバーコンテキストの構造"""
        response = client.get(reverse('trail_list'))

        assert 'source_choices' in response.context
        assert 'area_choices' in response.context
        assert 'status_choices' in response.context
        assert 'recent_sources' in response.context

    def test_sidebar_counts_accuracy(self, client, sample_trail_condition):
        """件数カウントの正確性"""
        response = client.get(reverse('trail_list'))

        # 情報源の件数が正しい
        source_choices = dict(response.context['source_choices'])
        assert sample_trail_condition.source.id in source_choices
```

---

### Phase 2: High（推奨・優先度2）

#### 3️⃣ `test_models.py` 作成

**新規ファイル**: `trail_status/tests/test_models.py`

**推定作業量**: 2時間
**推定テスト数**: 8-10個

```python
import pytest
from trail_status.models.condition import TrailCondition, AreaName, StatusType
from trail_status.models.mountain import MountainGroup
from trail_status.models.source import DataSource

class TestTrailCondition:
    def test_creation(self, db):
        """TrailCondition作成"""
        ...

    def test_str_representation(self, db):
        """__str__メソッド"""
        ...

    def test_get_absolute_url(self, db):
        """URL生成"""
        ...


class TestAreaName:
    def test_get_yamareco_area_id_okutama(self):
        """ヤマレコエリアID: 奥多摩"""
        area_id = AreaName.get_yamareco_area_id(AreaName.OKUTAMA)
        assert area_id == 306

    def test_get_yamareco_area_id_tanzawa(self):
        """ヤマレコエリアID: 丹沢"""
        area_id = AreaName.get_yamareco_area_id(AreaName.TANZAWA)
        assert area_id == 307
```

---

#### 4️⃣ `test_llm_stats.py` 作成

**新規ファイル**: `trail_status/tests/test_llm_stats.py`

**推定作業量**: 1-2時間
**推定テスト数**: 6-8個

---

#### 5️⃣ 管理コマンドテスト

**新規ファイル**: `trail_status/tests/test_commands.py`

**推定作業量**: 2-3時間

---

### Phase 3: Medium（任意・優先度3）

#### 6️⃣ 統合テスト

**新規ファイル**: `trail_status/tests/test_integration.py`

**推定作業量**: 3-4時間

---

## 📋 実装チェックリスト

### Critical（必須）

- [ ] `test_db_writer.py` 作成
  - [ ] `TestDbWriter` クラス
  - [ ] `TestRecordMatching` クラス
  - [ ] `TestSimilarityCalculation` クラス
  - [ ] `TestEdgeCases` クラス
- [ ] `test_views.py` 作成
  - [ ] `TestTrailListView` クラス
  - [ ] `TestTrailDetailView` クラス
  - [ ] `TestOtherPages` クラス
  - [ ] `TestSidebarContext` クラス

### High（推奨）

- [ ] `test_models.py` 作成
- [ ] `test_llm_stats.py` 作成
- [ ] `test_commands.py` 作成

### Medium（任意）

- [ ] `test_integration.py` 作成
- [ ] `test_slack_notifier.py` 作成

---

## 🛠️ テスト環境セットアップ

### pytest-cov インストール

カバレッジ可視化のため、pytest-covの追加を推奨：

```bash
# pyproject.tomlのdev dependenciesに追加
[dependency-groups]
dev = [
    "pytest-cov>=6.0.0",  # 追加
    ...
]

# インストール
uv sync --group dev
```

### カバレッジ測定コマンド

```bash
# カバレッジ測定
docker compose exec web uv run pytest --cov=trail_status --cov-report=html --cov-report=term

# HTMLレポート閲覧
# htmlcov/index.html をブラウザで開く
```

---

## 📊 期待される効果

### テスト追加前（現在）

```
テスト数: 19個
カバレッジ: 約40-50%
リスク: 名寄せアルゴリズムが未テスト
```

### Phase 1 完了後

```
テスト数: 約50個 (+31個)
カバレッジ: 約65-70% (+20-25%)
リスク: 大幅に低減
```

### Phase 2 完了後

```
テスト数: 約70個 (+51個)
カバレッジ: 約75-80% (+30-35%)
リスク: ほぼ解消
```

---

## 🎯 まとめ

### 現状の強み

- ✅ AI処理部分（fetcher, llm_client, pipeline）のテストは充実
- ✅ 基本的な動作は保証されている
- ✅ 19テスト全てパス

### 改善が必要な部分

- ⚠️ **中核の名寄せアルゴリズム（db_writer.py）がテストされていない**
- ⚠️ ユーザー向けビュー（views.py）がテストされていない
- ⚠️ モデル層の動作保証がない

### リスク評価

| リスク | 発生確率 | 影響度 | 対策優先度 |
|-------|---------|-------|-----------|
| db_writer.pyのバグ → 重複レコード | 中 | 大 | Critical |
| views.pyのバグ → UX低下 | 中 | 中 | Critical |
| models/のバグ → データ整合性 | 低 | 中 | High |

### 推奨アクション

1. **最優先**: `test_db_writer.py` 作成（4-6時間）
2. **次優先**: `test_views.py` 作成（2-3時間）
3. **その後**: `test_models.py` 作成（2時間）

**この3つを実装すれば、カバレッジは約70%に到達し、本番の安心感が大幅に向上します。**

---

## 📝 参考資料

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- プロジェクト内: `docs/my_docs/pytest使い方ガイド.md`
- プロジェクト内: `docs/my_docs/record-matching-algorithm.md`

---

**作成者**: Claude Sonnet 4.5
**最終更新**: 2026-02-06
