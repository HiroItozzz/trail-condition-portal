# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

登山道の危険情報を公的機関から自動収集・統合表示するWebアプリケーション。環境省、自治体、警察等の公式サイトから登山道危険情報を自動収集し、AI(DeepSeek/Gemini)による情報の構造化・正規化を行い、Django + PostgreSQLで管理・表示する。

## Tech Stack

- **Backend**: Django 6.0, PostgreSQL
- **Frontend**: Vite, TypeScript, Tailwind CSS 4.x
- **Data Collection**: httpx, trafilatura
- **AI Processing**: DeepSeek API, Gemini API, Pydantic
- **Task Scheduling**: django-apscheduler
- **Infrastructure**: Docker, uv (Python package manager)

## Common Commands

### Docker & Development

```bash
# コンテナ起動
docker compose up -d

# アプリケーション実行
docker compose exec web uv run manage.py runserver

# マイグレーション実行
docker compose exec web uv run manage.py migrate

# マイグレーション作成
docker compose exec web uv run manage.py makemigrations

# 管理画面スーパーユーザー作成
docker compose exec web uv run manage.py createsuperuser
```

### Testing & Code Quality

```bash
# テスト実行
uv run pytest

# 特定のテスト実行
uv run pytest trail_status/tests/test_specific.py

# 型チェック
uv run mypy .

# Ruff によるコードフォーマット
uv run ruff format

# Ruff によるリント
uv run ruff check

# Django テンプレートのフォーマット
uv run djlint templates/ trail_status/templates/ --reformat
```

### Custom Management Commands

```bash
# 登山道状況の同期（データ収集・AI解析・DB保存）
uv run manage.py trail_sync [options]
# Options:
#   --source <ID>       特定の情報源のみ処理
#   --dry-run           DB保存をスキップ（テスト用）
#   --model <name>      AIモデル指定（例: deepseek-chat, gemini-3-flash-preview）

# LLMテスト実行
uv run manage.py test_llm [options]

# データベース同期テスト
uv run manage.py test_db_sync
```

### Frontend

```bash
# フロントエンド開発サーバー起動（Dockerコンテナ内で自動起動）
cd frontend
npm install
npx vite build --watch  # ビルド監視モード

# 手動ビルド
npm run build
```

## Architecture

### High-Level Data Flow

1. **収集（Fetcher）**: 公的機関サイトから自動スクレイピング（httpx + trafilatura）
2. **変更検知**: ハッシュ比較で前回取得時からの変更を検出
3. **AI解析（Pipeline）**: 変更があった場合のみ DeepSeek/Gemini で構造化データ抽出
4. **照合・保存（DbWriter）**: 既存DBレコードと照合し、PostgreSQL に原文 + 正規化データを保存
5. **表示**: Django テンプレート + REST API で提供

### Core Components

#### trail_status/services/

- **pipeline.py**: データ収集からAI解析までの全体フロー制御（async処理）
- **fetcher.py**: HTTPリクエスト、trafilaturaによるテキスト抽出、ハッシュ計算
- **llm_client.py**: DeepSeek/Gemini APIクライアント、Pydantic Structured Output対応
- **llm_stats.py**: LLM使用状況の統計（トークン数、コスト計算、実行時間）
- **db_writer.py**: DB永続化を担当する`DbWriter`クラス
  - `save_to_source()`: DataSourceの更新（巡回日時、ハッシュ）
  - `save_condition_and_usage()`: TrailCondition + LlmUsage の保存（トランザクション管理）
  - `_reconcile_records()`: 既存DBレコードとAI出力の照合（3段階ハイブリッドアルゴリズム）
  - `_calculate_similarity()`: RapidFuzzによる複合類似度スコアリング
  - 詳細: [レコード同定アルゴリズム](../documents/record-matching-algorithm.md)
- **schema.py**: Pydantic モデル定義（AI出力スキーマ、内部データ構造）

#### trail_status/services/prompts/

YAMLファイルでプロンプトとAI設定を管理:
- **template.yaml**: 全情報源共通の基本プロンプト（原文保持、推論補完ルール）
- **{id:03d}_{prompt_key}.yaml**: 情報源ごとのカスタムプロンプト（例: 001_okutama_vc.yaml）
  - `prompt`: サイト固有の抽出ルール
  - `config`: model, temperature, thinking_budget, use_template

#### trail_status/models/

- **condition.py**: TrailCondition（登山道状況）、StatusType（通行止め、注意等）
- **source.py**: DataSource（情報源URL、プロンプトファイル、ハッシュキー）
- **mountain.py**: MountainGroup（山グループ）、AreaName（山域enum: 奥多摩、丹沢等）
- **llm_usage.py**: LlmUsage（AIモデル使用履歴：トークン数、コスト）

#### scheduler/

- **jobs.py**: 定期実行ジョブ（trail_sync コマンドを呼び出し）
- **scheduler.py**: django-apscheduler でのジョブ登録・管理

#### api/

- **views.py**: Django REST Framework ViewSets
- **serializers.py**: DRF Serializers
- **permissions.py**: 読み取り専用権限（AllowAny）

#### config/

- **settings.py**: Django設定（CORS、REST Framework、ログ、データベース）
- **urls.py**: ルートURL設定

### Frontend Integration

- **Vite**: Tailwind CSS 4.x をビルドし `static/dist/` に出力
- **Django**: `templates/` から Vite ビルド成果物を読み込み
- **開発時**: Docker Compose で frontend コンテナが自動ビルド監視

## Key Implementation Patterns

### Async Pipeline with Django ORM

- `trail_status/services/pipeline.py` は完全async実装（httpx.AsyncClient、AI API）
- Django ORM操作は `trail_status/services/db_writer.py` の `DbWriter` クラスで管理
- `DbWriter` はインスタンスが状態を保持する設計（`SourceSchemaSingle` と `ResultSingle` を保持）
- 管理コマンド `trail_sync.py` が非同期処理を `asyncio.run()` で実行し、結果を `DbWriter` に渡してDB保存

### Pydantic Structured Output

- `schema.py` の `TrailConditionSchemaAi` がAI出力スキーマを定義
- `llm_client.py` で OpenAI/Gemini SDK の structured output 機能を使用
- Pydantic Field の `description` がAIへのプロンプトとして機能

### Content Change Detection

- `DataSource.scraped_hash` に前回のHTML本文ハッシュを保存
- `fetcher.py` の `has_content_changed()` でハッシュ比較
- 変更なし→AI処理スキップでコスト削減

### Prompt Management

- YAMLファイルでプロンプトとAI設定をバージョン管理
- `LlmConfig.from_file()` で設定読み込み（CLI引数 > YAML > デフォルト）
- `use_template: true` で共通テンプレートと個別プロンプトを結合

### Record Matching Algorithm

- **3段階ハイブリッド同定**: 完全一致 → RapidFuzz類似度 → 新規作成
- **RapidFuzz使用**: 山名・登山道名・タイトル・説明の複合スコアリング
- **デフォルト閾値**: 0.7（調整可能）
- **詳細ドキュメント**: [record-matching-algorithm.md](../documents/record-matching-algorithm.md)

同定アルゴリズムの調整パラメータ（`db_writer.py` クラス定数 L37-58）:
- `SIMILARITY_THRESHOLD = 0.7`: 類似度判定閾値
- `FIELD_WEIGHT_*`: フィールド重み（山名0.3, 登山道0.3, タイトル0.25, 説明0.15）
- `BONUS_STATUS_MATCH = 0.1`: status一致ボーナス
- `BONUS_DATE_PROXIMITY = 0.05`: 日付近接ボーナス
- `DATE_PROXIMITY_DAYS = 14`: 日付近接判定範囲（±14日）
- `DESC_COMPARE_LENGTH = 100`: description比較文字数

## Environment Variables

Required in `.env`:
```
DATABASE_URL=postgresql://user:password@db:5432/dbname
DEEPSEEK_API_KEY=sk-...
GEMINI_API_KEY=...
IS_IDX=false  # Google IDX環境の場合 true
DJANGO_SECRET_KEY=...
```

## Testing Strategy

- `trail_status/tests/` にpytest テスト
- `pytest.ini_options` で `asyncio_mode = "auto"` 設定済み
- テストコマンド: `uv run pytest trail_status/tests/test_<module>.py`

## Important Notes

- **Python 3.13.7** 必須（uv で管理）
- **Django 6.0** を使用（最新メジャーバージョン）
- AI解析は変更検知時のみ実行（コスト最適化）
- プロンプトファイル名規則: `{source_id:03d}_{prompt_key}.yaml`
- ログは `logs/django.log` に記録（RotatingFileHandler、5MB制限）

## Production Deployment Checklist

### Priority 1: セキュリティ対応（必須）

- [ ] **DEBUG を環境変数化**: `DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"`
- [ ] **ALLOWED_HOSTS を環境変数化**: 本番ドメインを環境変数から読み込む
- [ ] **SECRET_KEY のデフォルト値削除**: 本番環境では環境変数必須にする
- [ ] **STATIC_ROOT 設定追加**: `STATIC_ROOT = BASE_DIR / "staticfiles"`
- [ ] **WhiteNoise 導入**: 静的ファイル配信用ミドルウェア

### Priority 2: 本番運用対応（必須）

- [ ] **Gunicorn 導入**: WSGIサーバー（`pyproject.toml`に追加）
- [ ] **本番用 Dockerfile 作成**: `Dockerfile.prod` など
- [ ] **docker-compose.prod.yml 作成**: 本番環境用の構成ファイル
- [ ] **.env.example 作成**: 環境変数テンプレート（API keyは空にする）
- [ ] **マイグレーション自動化**: デプロイ時の自動実行スクリプト

### Priority 3: 運用改善（推奨）

- [ ] **ヘルスチェックエンドポイント**: `/health/` など
- [ ] **エラートラッキング**: Sentry などの導入
- [ ] **nginx リバースプロキシ**: パフォーマンス向上
- [ ] **SSL/TLS 証明書**: Let's Encrypt など
- [ ] **定期バックアップ**: データベースバックアップスクリプト

### 現在の問題点

⚠️ **現在の設定は開発環境向け** - 以下の点が本番環境では不適切:
- `DEBUG = True` がハードコード
- `runserver` を使用（Dockerfile）
- CORS設定が開発用（localhost:5173）
- 静的ファイル配信設定が不足
