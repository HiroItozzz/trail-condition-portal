# CLAUDE.md

Claude Code on the web（クラウドのコンテナ）で作業するときの手順と注意点。

## セッション開始時に自動で行われること

`.claude/hooks/session-start.sh`（SessionStart フック）が次を行う。

- `uv sync --all-extras --all-groups`（Python 依存関係。ruff / mypy / pytest を含む）
- `frontend/` で `npm install`
- PostgreSQL 16 の起動と、DB `trail_portal_dev` の作成（ユーザー `postgres` / パスワード `postgres`）
- 次の環境変数の設定

| 変数 | 値 |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` |
| `DJANGO_SECRET_KEY` | 開発用のダミー値 |
| `DATABASE_URL` | `postgres://postgres:postgres@localhost:5432/trail_portal_dev` |

## よく使うコマンド

```bash
uv run pytest                        # 全テスト（86件）。テスト用DBは pytest-django が自動で作る
uv run pytest tests/trail_status/views/test_detail.py
uv run python manage.py migrate
uv run python manage.py check
uv run ruff check <変更したファイル>
uv run ruff format --check <変更したファイル>
uv run mypy <変更したファイル>
cd frontend && npx vite build        # フロントのビルド
```

## ブランチと PR の運用

### ブランチの役割
| ブランチ | 役割 |
|---|---|
| `main` | 本番。タグをつけると本番にデプロイされる（`cloudbuild.prod.yaml`） |
| `develop` | ステージング。push するだけで非公開の Cloud Run にデプロイされる（`cloudbuild.staging.yaml`）。DB は本番とは別の Supabase の DB |
| 作業ブランチ | 作業ごとに `main` から作り、`main` へ PR を出す。マージ後は削除する |

### コミットと push
- このリポジトリでは、Claude が自分で作った作業ブランチへのコミットと push はオーナーの確認なしで行ってよい。
- `main` へのコミット・push、タグの push、PR のマージはしない。
- `develop` への push は指示があったときだけ行う。

これらは `.claude/` の設定でも止めている。
- `.claude/hooks/guard-git.py`（PreToolUse フック）：`main` への push、タグの push、`main` ブランチでの commit を拒否し、`develop` への push は確認を求める
- `.claude/settings.json` の `permissions.deny`：GitHub MCP のマージ、自動マージ、ファイルの直接書き込み（`push_files` など）を禁止

### 作業ブランチの名前
`<種類>/<内容>` の形にする（例：`feat/email`、`fix/columnname`、`refac/llmclient`、`chore/claude-setup`）。種類はコミットメッセージの接頭辞に合わせる。

### develop の使い方
`develop` は `main` へ合流させるブランチではなく、ステージングで試すための使い捨ての枠として使う。

1. 作業ブランチで作業する
2. ステージングで試したいときは、作業ブランチを `develop` に force push する
3. 作業ブランチから `main` へ PR を出し、Squash でマージする
4. マージ後、`develop` を `main` に合わせる（force push）

- `develop` への push はステージングへのデプロイになるため、指示があったときだけ行う。
- `develop` を基準に作業しない。`develop` にしかない変更は残さない（必要なら作業ブランチに移して PR にする）。
- `develop` を上書きする前に、マイグレーションの差（`git diff --name-status origin/develop <ブランチ> -- '*/migrations/*'`）を確認する。ステージングの DB に適用済みのマイグレーションが消える場合は、先にオーナーに相談する。

### main のルールセット（GitHub）
- 削除と force push は禁止。
- 必須のステータスチェック：GitHub Actions の `test`（`.github/workflows/test.yml`）。
- 必須のデプロイ環境：`test`（同じワークフローが `environment: test` で実行する）。
- マージ前に、PR のブランチを最新の `main` に追従させる必要がある（Require branches to be up to date）。
- PR と承認はルール上は必須ではないが、運用ではオーナーが PR を確認してマージする。

### PR を出すとき
- PR の向き先は `main`。
- マージ方法は **Squash**（1つの PR が `main` の1コミットになる）。PR タイトルがそのままコミットメッセージになるので、`feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:` + 日本語で書く。
- Claude は PR をマージしない。マージはオーナーが行う。
- PR には Sourcery が自動でレビューをつける。指摘は参考にし、正しいか確かめてから対応する。

## 注意点

### `uv sync` は必ず `--all-extras --all-groups` をつける
`uv sync` は指定した構成に環境をぴったり合わせるため、オプションなしで実行すると `batch` / `analysis` extras（httpx、pydantic、google-genai など）が**削除される**。その結果、テストの収集時に `ModuleNotFoundError: No module named 'httpx'` になる。パッケージの追加・更新後も同じオプションで同期すること。

extras は本番の Web サーバーのイメージを軽くするために分けている（`Dockerfile.prod` の Web 用ステージは `--no-dev` のみ、バッチ用ステージは `--extra batch`）。データ収集・LLM 処理でだけ使うパッケージは `batch` に、分析用は `analysis` に追加し、`[project] dependencies` には Web サーバーが必要とするものだけを入れる。

### DB は PostgreSQL を使う
本番（Supabase）と CI（docker compose）はどちらも PostgreSQL。SQLite でもテストは通るが、差を避けるためにフックで起動した PostgreSQL 16 を使う。
PostgreSQL が止まっている場合は `service postgresql start` で起動する。

### 設定まわりの落とし穴
- `manage.py` の既定の設定は `config.settings.production`。`DJANGO_SETTINGS_MODULE` がないと「本番環境用のSECRET_KEYを設定してください」で止まる。
- `DEBUG` は設定しない（安全側の既定値 `False` のまま使う）。`DEBUG` は文字列 `"True"` と完全一致のときだけ有効（`base.py`）なので、コンテナに入っている `DEBUG=true`（小文字）も無効扱い。`DEBUG=False` のときは SQLite へのフォールバックがないため、`DATABASE_URL` が必須。
- `.env` は読み込まれない。`base.py` が読むのは `.env.sqlite3.local` だけ。

### Docker は使えない
`docker` コマンドはあるが daemon が動いていない。CI（`.github/workflows/test.yml`）の `docker compose` による手順はここでは再現できないので、上の `uv run pytest` で代わりに確認する。

### フロントのビルドは `npx vite build`
`npm run build` は `tsc && vite build` だが、`frontend/` に `tsconfig.json` がないため `tsc` がヘルプを表示して失敗する。本番（`Dockerfile.prod`）と同じ `npx vite build` を使う。

### ruff の既存の違反
リポジトリ全体では `ruff check` / `ruff format --check` に既存の違反がある（CI では実行していない）。確認は変更したファイルに絞り、無関係なファイルは直さない。

### 外部 API キーは設定されていない
LLM（Gemini / DeepSeek / OpenAI）や LangSmith、Slack のキーはない。テストはモックで動くので不要。実際の API を呼ぶ処理は動かさない。
