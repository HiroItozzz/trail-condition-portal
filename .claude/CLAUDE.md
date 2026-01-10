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
4. **保存（Synchronizer）**: PostgreSQL に原文 + 正規化データを保存
5. **表示**: Django テンプレート + REST API で提供

### Core Components

#### trail_status/services/

- **pipeline.py**: データ収集からAI解析までの全体フロー制御（async処理）
- **fetcher.py**: HTTPリクエスト、trafilaturaによるテキスト抽出、ハッシュ計算
- **llm_client.py**: DeepSeek/Gemini APIクライアント、Pydantic Structured Output対応
- **llm_stats.py**: LLM使用状況の統計（トークン数、コスト計算、実行時間）
- **synchronizer.py**: 既存DBデータとAI新規出力データの照合・同定処理（mountain_name_raw + trail_name で既存レコードを検索し、更新/新規作成リストを返却）
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
- Django ORM操作は `trail_status/services/synchronizer.py` で `sync_to_async` を使用
- 管理コマンド `trail_sync.py` が非同期処理を `asyncio.run()` で実行

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
