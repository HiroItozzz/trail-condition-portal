# feat/blog: 巡回ブログフィード機能追加レポート

## 概要

登山道危険情報の収集ソースとして、公的機関の**巡回ブログ（RSSフィード）** を新たに取り込む機能を追加。
既存の `data_format="WEB"` によるAI解析パイプラインとは独立した、フィード取得・DB同期の仕組みを構築した。

## 変更ファイル一覧（19ファイル, +941行）

### 新規作成

| ファイル | 内容 |
|---|---|
| `trail_status/models/feed.py` | BlogFeedモデル定義 |
| `trail_status/services/blog_fetcher.py` | フィード取得・パース・Pydanticスキーマ |
| `trail_status/management/commands/blog_sync.py` | ブログ同期バッチコマンド |
| `trail_status/templates/blogs.html` | ブログ一覧ページテンプレート（準備） |
| `trail_status/feed_samples/` | フィードデータのサンプル群（8ファイル） |

### 変更

| ファイル | 変更内容 |
|---|---|
| `trail_status/models/source.py` | `area_name` フィールド追加（BLOG用エリア分類） |
| `trail_status/models/condition.py` | `source` を `PROTECT` に変更、`url1` の `max_length=500` 追加 |
| `trail_status/admin.py` | BlogFeedAdmin追加、DataSourceに `data_format` 列追加 |
| `trail_status/urls.py` | `/blogs/` エンドポイント追加 |
| `trail_status/views.py` | `blogs_list` ビュー追加（準備） |

## 設計ポイント

### 1. BlogFeedモデル (`models/feed.py`)

- `source` ForeignKeyに `limit_choices_to={"data_format": "BLOG"}` でAdmin上の選択肢を制限
- `on_delete=PROTECT` で情報源の誤削除を防止
- `updated_at` は不要と判断（フィード記事は上書き更新しないため）
- ordering は `-published_at`（新しい投稿順）

### 2. Pydanticスキーマによるバリデーション (`services/blog_fetcher.py`)

- `BlogFeedSchema` で取得データをバリデーション
- `model_validator(mode="before")` で title / summary を正規化:
  - `html.unescape()` → HTMLエンティティ変換（`&nbsp;` 等）
  - `re.sub(r"<.*?>", "")` → HTMLタグ除去
  - 改行・全角スペース → 半角スペースに置換
  - title: 100文字、summary: 200文字で切り詰め
- `published_at` に `tzinfo=dt_timezone.utc` を付与（feedparserがUTC変換済みのため）
- Django側の `bulk_create` は `save()` / `full_clean()` を呼ばないため、Pydantic側でバリデーションを担保する設計（既存の TrailCondition パイプラインと同じ方針）

### 3. バッチコマンド (`commands/blog_sync.py`)

- `DataSource.objects.filter(data_format="BLOG")` でBLOGソースのみ取得
- `asyncio.gather` による非同期並列フィード取得
- URL集合の差分比較（`obtained_urls - existing_urls`）で新規記事のみ `bulk_create`
- 既存の `trail_sync` コマンドとは完全独立

### 4. DataSource拡張 (`models/source.py`)

- `area_name` フィールド追加（`blank=True, default=""`）
  - BLOGソースのエリア分類に使用
  - WEBソースは空のまま運用（WEB側はLLMが記事単位でエリア判定）
  - `mountain.py` からの import は一方向のため循環参照なし

### 5. 既存バッチへの影響

- `trail_sync` コマンドは `data_format="WEB"` でフィルタ済み
  - 全件処理時: `DataSource.objects.filter(data_format="WEB")`
  - 個別指定時: `source.data_format != "WEB"` チェックでBLOGを弾く
- 既存パイプラインへの影響なし

## 今後の課題

- [ ] `blogs_list` ビューの実装（カード/リスト形式での表示）
- [ ] `area_name` の運用開始（DataSourceへのエリア登録）
- [ ] Cloud Scheduler への `blog_sync` 登録
- [ ] schema.py に残っている旧 `BlogFeed` スキーマの削除
