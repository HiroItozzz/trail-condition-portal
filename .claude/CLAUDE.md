# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

登山道の危険情報を公的機関から自動収集・統合表示するWebアプリケーション。
- 本番URL: https://trail-info.jp/
- 環境省、自治体、警察等の公式サイトから登山道危険情報を自動収集
- AI（Gemini/DeepSeek/OpenAI）による情報の構造化・正規化
- RapidFuzz + SudachiPyによるテキスト類似度計算・名寄せ処理
- Django + PostgreSQLで管理・表示

## Tech Stack

- **Backend**: Django 6.0, PostgreSQL, Gunicorn, WhiteNoise
- **Frontend**: Tailwind CSS 4.x, Vite（`frontend/`ディレクトリ）
- **Data Collection**: httpx, trafilatura
- **AI Processing**: Gemini API, DeepSeek API, OpenAI API, Pydantic, LangSmith
- **Text Matching**: RapidFuzz, SudachiPy
- **Infrastructure**: Cloud Run, Supabase (PostgreSQL), Cloudflare, Docker, uv

## Common Commands

### Docker & Development

```bash
docker compose up -d
docker compose exec web uv run manage.py runserver
docker compose exec web uv run manage.py migrate
docker compose exec web uv run manage.py makemigrations
docker compose exec web uv run manage.py createsuperuser
```

### Testing & Code Quality

```bash
uv run pytest                                          # 全テスト実行
uv run pytest trail_status/tests/test_specific.py     # 特定テスト
uv run mypy .                                          # 型チェック
uv run ruff check                                      # リント
uv run ruff format                                     # フォーマット
uv run djlint templates/ trail_status/templates/ --reformat  # テンプレートフォーマット
```

### Custom Management Commands

```bash
uv run manage.py trail_sync [options]
#   --source <ID>       特定の情報源のみ処理
#   --dry-run           DB保存をスキップ
#   --model <name>      AIモデル指定
#   --new-hash          既存のハッシュを無視しLLM処理実行

uv run manage.py test_llm        # LLM接続テスト
uv run manage.py test_matching   # レコード照合アルゴリズムテスト
```

### Frontend Build

```bash
cd frontend
npm install
npx vite build           # CSS/JSビルド
npx vite build --watch   # ウォッチモード
```

## Architecture

### Data Flow

1. **収集（Fetcher）**: 公的機関サイトからスクレイピング（httpx + trafilatura）
2. **変更検知**: SHA-256ハッシュ比較（`DataSource.content_hash`）で前回からの変更を検出
3. **AI解析（Pipeline）**: 変更時のみ Gemini/DeepSeek/OpenAI で構造化データ抽出
4. **照合・保存（DbWriter）**: RapidFuzzで既存レコードと照合、PostgreSQLに保存
5. **表示**: Django テンプレートで提供

### Core Components

#### trail_status/services/

- **pipeline.py**: 全体フロー制御（完全async実装）
- **fetcher.py**: HTTP取得、trafilaturaテキスト抽出、ハッシュ計算
- **llm_client.py**: Gemini/DeepSeek/OpenAI APIクライアント、Pydantic Structured Output
- **db_writer.py**: DB永続化、レコード照合アルゴリズム
- **schema.py**: Pydanticモデル定義（AI出力スキーマ）

#### trail_status/services/prompts/

YAMLでプロンプトとAI設定を管理:
- **template.yaml**: 共通基本プロンプト
- **{id:03d}_{prompt_key}.yaml**: 情報源ごとのカスタムプロンプト

#### trail_status/models/

- **condition.py**: TrailCondition（登山道状況）、StatusType（9種類: CLOSURE, HAZARD, CLEAR, ANIMAL, WEATHER, FACILITY, WATER, SNOW, OTHER）
- **source.py**: DataSource（情報源URL、ハッシュ、last_checked_at）
- **mountain.py**: MountainGroup、AreaName
- **llm_usage.py**: LlmUsage（トークン数、コスト記録）

### Key Patterns

**Async Pipeline + Sync ORM**: pipeline.pyはasync、DB操作はDbWriterクラスで同期処理

**Content Change Detection**: `DataSource.content_hash`でハッシュ比較、変更なしはAI処理スキップ

**Record Matching**: 3段階ハイブリッド同定（完全一致 → RapidFuzz類似度 → 新規作成）
- 閾値: 0.7、フィールド重み（山名0.3, 登山道0.3, タイトル0.25, 説明0.15）
- 詳細: [record-matching-algorithm.md](../docs/my_docs/260123-record-matching-algorithm.md)

## Environment Variables

```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=...
DJANGO_SECRET_KEY=...
IS_PRODUCTION=True          # 本番環境フラグ
DJANGO_DEBUG=False          # デバッグモード
SCHEDULER_SECRET=...        # Cloud Scheduler Bearer token
SLACK_WEBHOOK_URL=...       # Slack通知（任意）
LANGSMITH_API_KEY=...       # LangSmithトレーシング（任意）
```

## Deployment

### Cloud Build + Cloud Run

- `cloudbuild.yaml`: ビルド・デプロイ定義
- マルチステージビルド: `server`（Web）と `batch`（バッチジョブ）
- イメージタグ: `$BRANCH_NAME:$COMMIT_SHA` と `$BRANCH_NAME:latest`

### URL Structure

- `/` - 登山道状況一覧
- `/trails?id=<id>` - 詳細表示
- `/site-policy/` - サイトポリシー
- `/admin/` - Django管理画面
- `/scheduler/run-sync/` - Cloud Schedulerウェブフック

## Important Notes

- **Python 3.13.7+** 必須（uv管理）
- **Timezone**: Asia/Tokyo (JST)
- AI解析は変更検知時のみ実行（コスト最適化）
- プロンプトファイル名規則: `{source_id:03d}_{prompt_key}.yaml`
- 本番ログはコンソール出力、開発時のみファイル出力（`logs/django.log`）
- **Supabase + select_related問題**: ForeignKeyの取得には`select_related`ではなく`prefetch_related`を使用すること。Supabase内部処理との相性で`select_related`を使うと60秒待たされる問題がある

## External APIs

### ヤマレコAPI

山名から座標・標高・周辺施設（山小屋、水場、危険個所等）を取得できる外部API。
- 詳細ページでヤマレコ検索リンクを提供（`AreaName.get_yamareco_area_id()`でエリアID変換）
- 将来的に「地図から探す」UI実装の基盤として活用予定
- テストツール: `tools/yamareco_poi_search.py`
- **詳細ドキュメント**: [yamareco-api.md](../docs/my_docs/260205-yamareco-api.md)
