#!/bin/bash
# Claude Code on the web 用のセッション開始フック。
# 依存関係の同期、PostgreSQL 16 の起動、テスト用の環境変数の設定を行う。
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# セッション中のコマンドに渡す環境変数（後続の処理が失敗しても必ず書く）
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  cat >> "$CLAUDE_ENV_FILE" <<'ENV'
export DJANGO_SETTINGS_MODULE=config.settings.development
export DJANGO_SECRET_KEY=insecure-claude-web-session-key
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/trail_portal_dev
ENV
fi

# extras をすべて入れる（extras なしの uv sync は batch/analysis を削除するため）
uv sync --all-extras --all-groups || echo "warn: uv sync に失敗した" >&2

(cd frontend && npm install --no-audit --no-fund) || echo "warn: npm install に失敗した" >&2

# PostgreSQL 16（コンテナにインストール済み・停止状態で起動する）
service postgresql start || echo "warn: PostgreSQL の起動に失敗した" >&2

ready=false
for _ in $(seq 1 30); do
  if pg_isready -q; then
    ready=true
    break
  fi
  sleep 1
done

if [ "$ready" = true ]; then
  su postgres -c "psql -q -c \"ALTER USER postgres PASSWORD 'postgres';\"" || echo "warn: postgres のパスワード設定に失敗した" >&2
  if ! su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='trail_portal_dev'\"" | grep -q 1; then
    su postgres -c "createdb trail_portal_dev" || echo "warn: DB の作成に失敗した" >&2
  fi
else
  echo "warn: PostgreSQL が起動しなかったため DB 作成をスキップした" >&2
fi

exit 0
