#!/bin/bash
# Claude Code on the web 用のセッション開始フック。
# 依存関係の同期、PostgreSQL 16 の起動、テスト用の環境変数の設定を行う。
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# extras をすべて入れる（extras なしの uv sync は batch/analysis を削除するため）
uv sync --all-extras --all-groups

(cd frontend && npm install --no-audit --no-fund)

# PostgreSQL 16（コンテナにインストール済み・停止状態で起動する）
service postgresql start
until pg_isready -q; do sleep 1; done
su postgres -c "psql -q -c \"ALTER USER postgres PASSWORD 'postgres';\""
if ! su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='trail_portal_dev'\"" | grep -q 1; then
  su postgres -c "createdb trail_portal_dev"
fi

# セッション中のコマンドに渡す環境変数
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  cat >> "$CLAUDE_ENV_FILE" <<'ENV'
export DJANGO_SETTINGS_MODULE=config.settings.development
export DJANGO_SECRET_KEY=insecure-claude-web-session-key
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/trail_portal_dev
ENV
fi
