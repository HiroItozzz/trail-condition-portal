# 本番環境デプロイガイド

## 📋 目次

1. [デプロイ前の準備](#デプロイ前の準備)
2. [WhiteNoise + Gunicorn 設定](#whitenoise--gunicorn-設定)
3. [SSL/TLS 対応の選択肢](#ssltls-対応の選択肢)
4. [本番用 Docker 設定](#本番用-docker-設定)
5. [デプロイ手順](#デプロイ手順)
6. [トラブルシューティング](#トラブルシューティング)
7. [nginx への移行（将来的に必要な場合）](#nginx-への移行将来的に必要な場合)

---

## デプロイ前の準備

### ✅ チェックリスト

- [X] ドメイン取得済み
- [X] 環境変数の準備（`.env.production` 作成）
- [ ] データベースのバックアップ
- [X] デプロイ先の選定（AWS/GCP/VPS/PaaS）

### 📝 必須環境変数

`.env.production` ファイルを作成：

```bash
# Django
DJANGO_SECRET_KEY=<ランダムな文字列（50文字以上推奨）>
DJANGO_DEBUG=False
ALLOWED_HOSTS=

# Database
DATABASE_URL=postgresql://user:password@db:5432/dbname

# AI API
DEEPSEEK_API_KEY=sk-...
GEMINI_API_KEY=...

# PostgreSQL（docker-compose用）
POSTGRES_DB=trail_condition_prod
POSTGRES_USER=trail_user
POSTGRES_PASSWORD=<強力なパスワード>

# Optional: Slack通知
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### 🔑 SECRET_KEY の生成方法

```python
# Python で実行
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

または：
```bash
docker compose exec web uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## WhiteNoise + Gunicorn 設定

### 1. 依存関係の追加

`pyproject.toml` の `dependencies` に追加：

```toml
dependencies = [
    # ... 既存の依存関係
    "gunicorn>=23.0.0",
    "whitenoise>=6.8.2",
]
```

インストール：
```bash
uv sync
```

### 2. settings.py の変更

#### MIDDLEWARE に WhiteNoise を追加

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ← SecurityMiddleware の直後に追加
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # ...
]
```

#### STATIC_ROOT の設定

```python
# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# 本番環境用：collectstatic で全静的ファイルを集める場所
STATIC_ROOT = BASE_DIR / "staticfiles"
```

#### WhiteNoise のストレージ設定（オプション）

圧縮とキャッシュ最適化を有効にする：

```python
# Django 5.1+ の STORAGES 設定
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

#### ALLOWED_HOSTS の環境変数化

```python
import os

# 環境変数から読み込み（カンマ区切り）
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
```

#### CSRF_TRUSTED_ORIGINS の本番設定

```python
# 本番環境用（環境変数で切り替え）
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        "https://your-domain.com",
        "https://www.your-domain.com",
    ]
```

#### CORS 設定の本番対応

```python
# 本番環境では特定のオリジンのみ許可
if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
else:
    # 本番環境：フロントエンドが別ドメインの場合のみ設定
    # 同一ドメインなら不要
    CORS_ALLOWED_ORIGINS = []
```

### 3. SECRET_KEY のデフォルト値削除（セキュリティ強化）

環境変数必須にする：

```python
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable is required")
```

ただし、開発環境では煩雑なので、開発時のみデフォルト値を使う方法もあり：

```python
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only" if DEBUG else None
)

if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY is required in production")
```

---

## SSL/TLS 対応の選択肢

**重要**: WhiteNoise は静的ファイル配信のみで、SSL 終端は**できません**。

### オプション 1: クラウドロードバランサー（推奨）

AWS、GCP、Azure などのマネージドサービスを使用。

```
[ユーザー]
  ↓ HTTPS
[AWS ALB / GCP Load Balancer] ← SSL 終端
  ↓ HTTP（内部通信）
[Docker コンテナ]
```

**メリット**:
- 証明書の自動更新
- DDoS 対策
- ヘルスチェック機能
- スケーリングが容易

**設定例（AWS ALB）**:
- ALB でリスナー（443番ポート）を作成
- ACM（AWS Certificate Manager）で証明書を発行
- ターゲットグループに Docker コンテナを登録

Django 側の設定追加：

```python
# settings.py
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

### オプション 2: nginx リバースプロキシ + Let's Encrypt

VPS や自前サーバーの場合。

```
[ユーザー]
  ↓ HTTPS
[nginx コンテナ] ← SSL 終端（Let's Encrypt）
  ↓ HTTP（内部通信）
[Django コンテナ]
```

詳細は後述の「[nginx への移行](#nginx-への移行将来的に必要な場合)」を参照。

### オプション 3: Cloudflare（簡易運用）

```
[ユーザー]
  ↓ HTTPS
[Cloudflare] ← SSL 終端
  ↓ HTTP or HTTPS（Flexible/Full）
[あなたのサーバー]
```

**メリット**:
- 無料で SSL 対応
- DDoS 対策
- CDN 機能
- DNS 管理も統合

**設定手順**:
1. Cloudflare にドメインを追加
2. DNS レコードを設定（A レコード等）
3. SSL/TLS モードを「Flexible」または「Full」に設定
4. あなたのサーバーは HTTP で待ち受け

Django 側は上記のプロキシ設定を追加。

---

## 本番用 Docker 設定

### Dockerfile.prod

開発用とは別に本番用 Dockerfile を作成：

```dockerfile
FROM python:3.13-slim

WORKDIR /code

# uvをインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 依存関係をコピー＆インストール
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

# アプリケーションコードをコピー
COPY . .

# 静的ファイルを収集（ビルド時に実行）
# 注意：環境変数が必要な場合は実行時に collectstatic を実行
# RUN uv run manage.py collectstatic --noinput

# Gunicorn で起動
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
```

**ワーカー数の目安**:
```
ワーカー数 = (2 × CPUコア数) + 1
```

例：
- 2コア → 5 workers
- 4コア → 9 workers

### docker-compose.prod.yml

本番用の docker-compose ファイル：

```yaml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: >
      sh -c "uv run manage.py migrate &&
             uv run manage.py collectstatic --noinput &&
             uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120"
    ports:
      - "${PORT:-8000}:8000"
    environment:
      - PYTHONDONTWRITEBITECODE=1
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:18-alpine
    env_file:
      - .env.production
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-trail_user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data_prod:
```

**開発用との違い**:
- ボリュームマウントなし（コードはコンテナに固定）
- frontend コンテナなし（ビルド済み静的ファイルを使用）
- `restart: unless-stopped` で自動再起動
- ヘルスチェック設定
- `.env.production` を使用

### .env.example の作成

リポジトリに含める環境変数のテンプレート：

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database
DATABASE_URL=postgresql://user:password@db:5432/dbname
POSTGRES_DB=trail_condition_prod
POSTGRES_USER=trail_user
POSTGRES_PASSWORD=your-strong-password

# AI API
DEEPSEEK_API_KEY=your-api-key
GEMINI_API_KEY=your-api-key

# Optional
SLACK_WEBHOOK_URL=
```

**注意**: 実際の値は含めず、テンプレートのみコミット。

---

## デプロイ手順

### 1. 事前準備

```bash
# リポジトリをサーバーにクローン
git clone https://github.com/your-username/trail-condition-portal.git
cd trail-condition-portal

# .env.production を作成
cp .env.example .env.production
# エディタで実際の値を設定
nano .env.production
```

### 2. フロントエンドのビルド（初回のみ）

```bash
cd frontend
npm install
npm run build
cd ..
```

ビルド成果物が `static/dist/` に出力されます。

### 3. Docker イメージのビルド

```bash
docker compose -f docker-compose.prod.yml build
```

### 4. データベースの起動

```bash
docker compose -f docker-compose.prod.yml up -d db
```

### 5. マイグレーションと静的ファイル収集

```bash
# マイグレーション
docker compose -f docker-compose.prod.yml run --rm web uv run manage.py migrate

# 静的ファイル収集
docker compose -f docker-compose.prod.yml run --rm web uv run manage.py collectstatic --noinput

# スーパーユーザー作成（初回のみ）
docker compose -f docker-compose.prod.yml run --rm web uv run manage.py createsuperuser
```

### 6. アプリケーション起動

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 7. 動作確認

```bash
# ログ確認
docker compose -f docker-compose.prod.yml logs -f web

# ヘルスチェック
curl http://localhost:8000/admin/
```

### 8. データ収集ジョブの確認

```bash
# 手動でデータ同期をテスト
docker compose -f docker-compose.prod.yml exec web uv run manage.py trail_sync --dry-run

# スケジューラーが動作しているか確認
docker compose -f docker-compose.prod.yml exec web uv run manage.py shell
>>> from scheduler.jobs import sync_trail_conditions
>>> sync_trail_conditions()  # 手動実行
```

---

## トラブルシューティング

### 問題 1: 静的ファイルが 404

**症状**: CSS/JS が読み込まれない、admin ページのスタイルが崩れる

**原因**:
- `collectstatic` が実行されていない
- `STATIC_ROOT` が未設定
- WhiteNoise が正しく設定されていない

**解決方法**:
```bash
# 静的ファイルを再収集
docker compose -f docker-compose.prod.yml exec web uv run manage.py collectstatic --noinput

# STATIC_ROOT の確認
docker compose -f docker-compose.prod.yml exec web ls -la /code/staticfiles/

# settings.py で WhiteNoise の順序を確認（SecurityMiddleware の直後）
```

### 問題 2: ALLOWED_HOSTS エラー

**症状**: `DisallowedHost at /` エラー

**原因**: `ALLOWED_HOSTS` にアクセス元のホスト名が含まれていない

**解決方法**:
```python
# .env.production を確認
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,localhost,127.0.0.1

# または settings.py で直接設定
ALLOWED_HOSTS = [
    "your-domain.com",
    "www.your-domain.com",
]
```

### 問題 3: Database connection failed

**症状**: `could not connect to server: Connection refused`

**原因**: データベースが起動していない、または接続情報が間違っている

**解決方法**:
```bash
# データベースの状態確認
docker compose -f docker-compose.prod.yml ps db

# ログ確認
docker compose -f docker-compose.prod.yml logs db

# DATABASE_URL の確認
docker compose -f docker-compose.prod.yml exec web env | grep DATABASE_URL
```

### 問題 4: Gunicorn タイムアウト

**症状**: `[CRITICAL] WORKER TIMEOUT`

**原因**: リクエスト処理に時間がかかりすぎている

**解決方法**:
```dockerfile
# Dockerfile.prod で timeout を延長
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "300"]
```

AI 解析など重い処理がある場合は、タイムアウトを長めに設定。

### 問題 5: SECRET_KEY が見つからない

**症状**: `ValueError: DJANGO_SECRET_KEY environment variable is required`

**原因**: `.env.production` に `DJANGO_SECRET_KEY` が設定されていない

**解決方法**:
```bash
# SECRET_KEY を生成
docker compose -f docker-compose.prod.yml run --rm web uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# .env.production に追加
echo "DJANGO_SECRET_KEY=生成された文字列" >> .env.production

# コンテナを再起動
docker compose -f docker-compose.prod.yml restart web
```

---

## nginx への移行（将来的に必要な場合）

WhiteNoise で運用中に、以下の状況になったら nginx を検討：

- 同時接続数が数千〜数万に増えた
- 複数のアプリケーションを統合したい
- より高度なキャッシュ制御が必要
- SSL 証明書を自前で管理したい（Let's Encrypt）

### nginx 追加の手順

#### 1. nginx.conf を作成

```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Let's Encrypt の検証用
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # HTTP → HTTPS リダイレクト
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL 証明書
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL 設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 静的ファイルは nginx が直接配信
    location /static/ {
        alias /staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # メディアファイル（将来的に画像アップロード等が必要な場合）
    location /media/ {
        alias /media/;
        expires 7d;
    }

    # その他のリクエストは Django へプロキシ
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # タイムアウト設定
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

#### 2. docker-compose.prod.yml に nginx を追加

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./staticfiles:/staticfiles:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - web
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

  web:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: >
      sh -c "uv run manage.py migrate &&
             uv run manage.py collectstatic --noinput &&
             uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4"
    expose:
      - "8000"  # ports ではなく expose（nginx からのみアクセス可能）
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    # ... 変更なし
```

#### 3. Let's Encrypt 証明書の取得

```bash
# 初回証明書取得（事前に nginx を起動しておく）
docker compose -f docker-compose.prod.yml run --rm certbot certonly --webroot --webroot-path=/var/www/certbot -d your-domain.com -d www.your-domain.com --email your-email@example.com --agree-tos --no-eff-email

# nginx を再起動して証明書を読み込み
docker compose -f docker-compose.prod.yml restart nginx
```

#### 4. settings.py から WhiteNoise を削除（オプション）

nginx で静的ファイルを配信する場合、WhiteNoise は不要になります：

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # "whitenoise.middleware.WhiteNoiseMiddleware",  # ← コメントアウトまたは削除
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ...
]
```

ただし、WhiteNoise を残しておいても問題ありません（nginx が優先されます）。

---

## まとめ

### 推奨デプロイ構成

**小〜中規模（最初はこれ）**:
```
[Cloudflare or AWS ALB]
  ↓ HTTPS
[Docker: Gunicorn + WhiteNoise]
  ↓
[PostgreSQL]
```

**大規模 or 複雑な要件**:
```
[Cloudflare]
  ↓ HTTPS
[nginx]
  ↓ HTTP
[Docker: Gunicorn]
  ↓
[PostgreSQL]
```

### 次のステップ

1. ✅ WhiteNoise + Gunicorn で本番環境を構築
2. ✅ SSL は Cloudflare or クラウドロードバランサーで対応
3. ⏳ 運用しながらパフォーマンスを監視
4. ⏳ 必要に応じて nginx へ移行

---

**作成日**: 2026-01-16
**最終更新**: 2026-01-16
