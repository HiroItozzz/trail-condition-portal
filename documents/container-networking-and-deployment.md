# コンテナ通信とデプロイ詳細ガイド

リバースプロキシ、コンテナ間通信、Cloudflare、GCP Cloud Run について詳しく解説します。

---

## 📋 目次

1. [リバースプロキシとは](#リバースプロキシとは)
2. [nginx vs Cloudflare - 役割の違い](#nginx-vs-cloudflare---役割の違い)
3. [コンテナ間通信の仕組み](#コンテナ間通信の仕組み)
4. [Cloudflare セットアップ完全ガイド](#cloudflare-セットアップ完全ガイド)
5. [GCP Cloud Run デプロイガイド](#gcp-cloud-run-デプロイガイド)
6. [構成パターン別コスト比較](#構成パターン別コスト比較)

---

## リバースプロキシとは

### 基本概念

**リバースプロキシ** = クライアントとバックエンドサーバーの間に立つ仲介者

```
[ユーザー]
  ↓ HTTPS
[リバースプロキシ] ← ここでSSL終端
  ↓ HTTP
[バックエンドサーバー]
```

### 主な役割

1. **SSL/TLS 終端**
   - HTTPS を受けて HTTP に変換
   - 証明書の管理
   - 暗号化/復号化の負荷をバックエンドから分離

2. **セキュリティレイヤー**
   - バックエンドのIPアドレスを隠す
   - 攻撃を防ぐフィルター
   - レート制限

3. **負荷分散**
   - 複数のバックエンドサーバーに振り分け
   - ヘルスチェック

4. **キャッシュ**
   - 静的コンテンツのキャッシュ
   - レスポンス高速化

### なぜ SSL 終端後は HTTP で良いのか？

```
[インターネット（危険）]
  ↓ HTTPS（暗号化必須）
[リバースプロキシ]
  ↓ HTTP（暗号化不要）
[信頼できる内部ネットワーク]
```

**理由**:
- リバースプロキシとバックエンド間は**信頼できるネットワーク**
- 同じサーバー内、または VPC 内の通信
- 暗号化のオーバーヘッドが不要
- **パフォーマンス向上**

**例外** - HTTPS が必要な場合:
- リバースプロキシとバックエンドが**別のデータセンター**
- インターネット経由での通信
- コンプライアンス要件（金融系など）

---

## nginx vs Cloudflare - 役割の違い

どちらも「リバースプロキシ」だけど、**位置と役割が違う**

### nginx（サーバーサイド リバースプロキシ）

#### 位置
```
[ユーザー]
  ↓ インターネット
[あなたのサーバー]
  └─ nginx ← ここ！サーバー内
      ↓ 同じマシン内 or Docker内部ネットワーク
    [Django]
```

#### 役割

| 機能 | 説明 |
|------|------|
| **SSL 終端** | Let's Encrypt で証明書取得・管理 |
| **静的ファイル配信** | `/static/` を直接配信（Django を経由しない） |
| **リバースプロキシ** | Django へリクエストを転送 |
| **URL rewrite** | `/api/v1/` → `/` など |
| **レート制限** | IP単位でリクエスト制限 |
| **圧縮** | gzip 圧縮 |

#### nginx.conf の例

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # 静的ファイルは nginx が直接配信
    location /static/ {
        alias /var/www/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # その他は Django へプロキシ
    location / {
        proxy_pass http://localhost:8000;  # ← HTTP！
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**特徴**:
- ✅ サーバー内で完結
- ✅ 細かい制御が可能
- ✅ 無料（オープンソース）
- ⚠️ 設定ファイルを書く必要あり
- ⚠️ 証明書管理が必要

---

### Cloudflare（グローバル CDN + リバースプロキシ）

#### 位置
```
[ユーザー（東京）]
  ↓ 近くのデータセンターに自動接続
[Cloudflare 東京データセンター] ← ここ！世界中に分散
  ↓ インターネット経由
[あなたのサーバー（どこでもOK）]
```

#### 役割

| 機能 | 説明 | nginx との違い |
|------|------|----------------|
| **SSL 終端** | 無料で SSL 証明書を自動発行・更新 | Let's Encrypt 不要 |
| **グローバル CDN** | 世界200+箇所にキャッシュサーバー | nginx は1箇所のみ |
| **DDoS 対策** | 大規模攻撃を自動ブロック | nginx では不可 |
| **WAF** | SQLインジェクション等を検知・ブロック | nginx では複雑 |
| **DNS 管理** | ドメインのDNS設定を統合管理 | nginx は DNS 不可 |
| **アクセス解析** | リアルタイムの統計情報 | nginx では別途設定 |

#### Cloudflare の仕組み

```
[日本のユーザー]
  ↓ HTTPS
[Cloudflare 東京DC]（キャッシュあり→即レスポンス）
  ↓ キャッシュなし→
[Cloudflare グローバルネットワーク]
  ↓ 最適経路で接続
[あなたのサーバー（米国VPSでもOK）]
```

**ユーザーから見ると**:
- 日本のユーザー → 東京のCloudflareサーバーに接続（超高速）
- 米国のユーザー → 米国のCloudflareサーバーに接続
- サーバーがどこにあっても、ユーザーは近くのCDNから取得

**特徴**:
- ✅ 設定が超簡単（DNS設定のみ）
- ✅ SSL 自動管理（証明書の心配不要）
- ✅ グローバル配信
- ✅ DDoS 対策が最強
- ✅ 無料プランでも強力
- ⚠️ すべてのトラフィックがCloudflare経由
- ⚠️ Cloudflare ダウン時の影響

---

### 比較表

| 項目 | nginx | Cloudflare |
|------|-------|------------|
| **位置** | サーバー内 | 世界中に分散 |
| **SSL管理** | 手動（Let's Encrypt） | 自動（無料） |
| **CDN** | ❌ | ✅（世界200+箇所） |
| **DDoS対策** | ⚠️（基本的な対策のみ） | ✅（テラビット級の攻撃も防御） |
| **WAF** | ⚠️（ModSecurity等が必要） | ✅（無料プランでも） |
| **静的ファイル配信** | サーバーから | キャッシュから（超高速） |
| **設定難易度** | ⭐⭐⭐ | ⭐ |
| **コスト** | 無料（サーバー代のみ） | 無料〜 |
| **細かい制御** | ✅ | ⚠️（UIベース） |

---

## コンテナ間通信の仕組み

### Docker のネットワーク概念

Docker Compose を使うと、**仮想的なネットワーク**が自動作成されます。

```yaml
services:
  nginx:
    # ...
  web:
    # ...
  db:
    # ...

networks:
  app-network:  # ← 仮想ネットワーク
    driver: bridge
```

このネットワーク内では：
- ✅ コンテナ同士が**サービス名で通信**できる
- ✅ 外部から隔離されている
- ✅ 暗号化不要（同じマシン内の仮想ネットワーク）

---

### 実例：nginx + Django + PostgreSQL

#### docker-compose.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"      # ← 外部公開（HTTP）
      - "443:443"    # ← 外部公開（HTTPS）
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./staticfiles:/staticfiles:ro
    depends_on:
      - web
    networks:
      - app-network

  web:
    build: .
    expose:        # ← expose（外部非公開）
      - "8000"
    environment:
      - DATABASE_URL=postgresql://trail_user:password@db:5432/trail_condition
    depends_on:
      - db
    networks:
      - app-network

  db:
    image: postgres:18-alpine
    expose:        # ← expose（外部非公開）
      - "5432"
    environment:
      - POSTGRES_DB=trail_condition
      - POSTGRES_USER=trail_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
```

#### 通信の流れ

```
[外部のユーザー]
  ↓ HTTPS（443） - インターネット経由
[nginx コンテナ] ← ★ ここだけが外部公開
  |
  | SSL 終端（HTTPS → HTTP変換）
  |
  ↓ HTTP - Docker内部ネットワーク（app-network）
  ↓ http://web:8000  ← サービス名で通信
[web コンテナ（Django + Gunicorn）]
  |
  ↓ PostgreSQLプロトコル - Docker内部ネットワーク
  ↓ postgresql://db:5432  ← サービス名で通信
[db コンテナ（PostgreSQL）]
```

---

### ポイント解説

#### 1. `ports` vs `expose`

| 設定 | 意味 | 外部アクセス |
|------|------|-------------|
| **ports: - "80:80"** | ホストマシンのポート80をコンテナの80に公開 | ✅ 可能 |
| **expose: - "8000"** | コンテナ間通信のみ許可 | ❌ 不可 |

**セキュリティのベストプラクティス**:
- nginx のみ `ports` で外部公開
- Django と PostgreSQL は `expose` のみ（内部通信のみ）

---

#### 2. サービス名での通信

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'trail_condition',
        'USER': 'trail_user',
        'PASSWORD': 'password',
        'HOST': 'db',  # ← コンテナ名（サービス名）
        'PORT': '5432',
    }
}
```

```nginx
# nginx.conf
upstream django {
    server web:8000;  # ← コンテナ名（サービス名）
}

server {
    location / {
        proxy_pass http://django;  # ← upstream名
    }
}
```

Docker の**内部DNS**が自動的に解決：
- `web` → `172.18.0.3`（自動割り当てのIPアドレス）
- `db` → `172.18.0.4`

IP アドレスは起動ごとに変わるけど、**サービス名は不変**！

---

#### 3. なぜ HTTP で良いのか？

```
┌─────────────────────────────────────┐
│ ホストマシン                          │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ app-network（仮想ネットワーク）│  │
│  │                              │  │
│  │  [nginx] ──HTTP──> [web]    │  │
│  │                ↓             │  │
│  │              [db]            │  │
│  │                              │  │
│  └──────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
```

- すべて**同じマシン内の仮想ネットワーク**
- 外部からアクセス不可
- カーネルレベルで隔離されている
- 暗号化のオーバーヘッド不要

**もし別マシンなら**:
```
[マシンA: nginx] ──インターネット──> [マシンB: Django]
                  ↑ HTTPS 必須
```

---

## Cloudflare セットアップ完全ガイド

### 前提条件

- ドメイン取得済み（お名前.com、ムームードメイン等）
- サーバー準備済み（VPS、AWS EC2 等）

---

### ステップ1: Cloudflare アカウント作成

1. https://cloudflare.com にアクセス
2. 「Sign Up」でアカウント作成
3. メール認証

---

### ステップ2: ドメインを追加

1. ダッシュボードで「Add a Site」をクリック
2. ドメイン名を入力（例: `trail-condition.com`）
3. 無料プランを選択
4. Cloudflare がドメインの既存DNS設定をスキャン

---

### ステップ3: ネームサーバーを変更

Cloudflare が提示するネームサーバーに変更：

```
現在のネームサーバー（お名前.com等）:
  ns1.example.com
  ns2.example.com

Cloudflareのネームサーバー（例）:
  chad.ns.cloudflare.com
  june.ns.cloudflare.com
```

#### お名前.com の場合

1. お名前.com にログイン
2. 「ドメイン設定」→「ネームサーバーの設定」→「ネームサーバーの変更」
3. Cloudflare のネームサーバーを入力
4. 保存

**反映時間**: 数時間〜24時間

---

### ステップ4: DNS レコード設定

Cloudflare ダッシュボード → DNS → Records

#### A レコードを追加

| Type | Name | Content | Proxy status |
|------|------|---------|--------------|
| A | @ | `123.456.789.0`（サーバーのIP） | Proxied（オレンジ雲） |
| A | www | `123.456.789.0` | Proxied |

**Proxy status の意味**:
- **Proxied**（オレンジ雲）: Cloudflare 経由（CDN、DDoS対策 ON）
- **DNS only**（灰色雲）: 直接接続（Cloudflare 経由しない）

**推奨**: Proxied（オレンジ雲）

---

### ステップ5: SSL/TLS 設定

Cloudflare ダッシュボード → SSL/TLS

#### SSL/TLS 暗号化モードを選択

| モード | Cloudflare↔ユーザー | Cloudflare↔サーバー | 説明 |
|--------|---------------------|---------------------|------|
| **Off** | HTTP | HTTP | SSL なし（非推奨） |
| **Flexible** | HTTPS | HTTP | 一番簡単、サーバー側はHTTPでOK |
| **Full** | HTTPS | HTTPS | サーバー側も SSL 必要（自己証明書OK） |
| **Full (strict)** | HTTPS | HTTPS | 正式な証明書が必要 |

**推奨の段階的アプローチ**:
1. 最初は **Flexible** で始める（簡単）
2. 動作確認後、**Full (strict)** に変更（最も安全）

#### Flexible モードでの構成

```
[ユーザー]
  ↓ HTTPS（Cloudflare が自動で証明書発行）
[Cloudflare]
  ↓ HTTP
[サーバー: Docker（Gunicorn）]
  ← サーバー側は HTTP で待ち受け
  ← 証明書不要！
```

**Django 側の設定** (settings.py):

```python
# Cloudflare を信頼する設定
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 本番環境のみ
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # HTTP → HTTPS リダイレクト
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

---

### ステップ6: ファイアウォール設定（オプション）

Cloudflare ダッシュボード → Security → WAF

無料プランでも以下が使える：
- **SQLインジェクション検知**
- **XSS 攻撃ブロック**
- **レート制限**（有料プランでより高度）

---

### ステップ7: キャッシュ設定

Cloudflare ダッシュボード → Caching → Configuration

```
Browser Cache TTL: 4 hours（推奨）
Caching Level: Standard
```

#### ページルールでキャッシュ制御（無料プランで3ルールまで）

例：静的ファイルのキャッシュを強化

```
URL: *trail-condition.com/static/*
Settings:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month
```

---

### ステップ8: 動作確認

```bash
# DNS が正しく設定されているか確認
dig trail-condition.com

# SSL 証明書を確認
curl -I https://trail-condition.com

# Cloudflare 経由か確認（レスポンスヘッダー）
curl -I https://trail-condition.com | grep -i cf-ray
# → CF-RAY: xxx-NRT （Cloudflare 経由の証明）
```

---

### Full (strict) モードへの移行（推奨）

より安全な構成にするため、サーバー側にも SSL 証明書を設定：

#### 1. Cloudflare Origin CA 証明書を発行

Cloudflare ダッシュボード → SSL/TLS → Origin Server → Create Certificate

- Cloudflare が専用証明書を発行（無料）
- 15年有効
- サーバーにインストール

#### 2. nginx に証明書を設定

```nginx
server {
    listen 443 ssl http2;
    server_name trail-condition.com;

    # Cloudflare Origin CA 証明書
    ssl_certificate /etc/ssl/cloudflare/cert.pem;
    ssl_certificate_key /etc/ssl/cloudflare/key.pem;

    # ...
}
```

#### 3. Cloudflare で Full (strict) に変更

SSL/TLS → Overview → Encryption mode: **Full (strict)**

これで完璧な構成：

```
[ユーザー]
  ↓ HTTPS（Cloudflare 証明書）
[Cloudflare]
  ↓ HTTPS（Origin CA 証明書で検証）
[サーバー]
```

---

## GCP Cloud Run デプロイガイド

### Cloud Run とは

**フルマネージドなコンテナ実行環境**

- Dockerコンテナをアップロードするだけで動く
- オートスケール（0インスタンス〜自動）
- 従量課金（使った分だけ）
- SSL 自動管理
- グローバル配信（Google のインフラ）

---

### 無料枠（重要！）

#### Cloud Run の無料枠

| リソース | 無料枠（月） | 超過後の料金 |
|---------|-------------|-------------|
| **リクエスト** | 200万回 | $0.40 / 100万リクエスト |
| **CPU 時間** | 180,000 vCPU秒 | $0.00002400 / vCPU秒 |
| **メモリ** | 360,000 GiB秒 | $0.00000250 / GiB秒 |
| **ネットワーク送信** | 1 GB | $0.12 / GB |

**計算例**（月間1万リクエスト、平均レスポンス0.5秒、メモリ512MB）:
- リクエスト: 10,000回 → **無料**
- CPU: 10,000 × 0.5秒 = 5,000 vCPU秒 → **無料**
- メモリ: 10,000 × 0.5秒 × 0.5GB = 2,500 GiB秒 → **無料**

**小規模なら完全無料で運用可能！**

---

#### Cloud SQL の料金（注意）

**Cloud SQL には無料枠がありません**

| インスタンス | 月額料金 |
|-------------|----------|
| db-f1-micro（0.6GB RAM） | **$7.67/月**（常時起動） |
| db-g1-small（1.7GB RAM） | **$25.00/月** |

**コスト削減のオプション**:

##### オプション A: 外部 PostgreSQL を使う

- **Supabase**（無料プラン: 500MB、2週間非アクティブで停止）
- **ElephantSQL**（無料プラン: 20MB）
- **Railway**（$5/月〜）

##### オプション B: SQLite を使う（小規模のみ）

Cloud Run は**エフェメラルストレージ**なので、SQLiteは推奨されません。

##### オプション C: Cloud SQL + WhiteNoise + Cloudflare を VPS で運用

→ VPS（月$5〜）の方が安い可能性

---

### 推奨構成

**小規模**（月間数千〜1万リクエスト）:

```
[Cloudflare]（無料）
  ↓
[Cloud Run]（無料枠内）
  ↓
[Supabase PostgreSQL]（無料）
```

**月額**: $0

---

**中規模**（月間数万リクエスト）:

```
[Cloudflare]（無料）
  ↓
[Cloud Run]（無料枠 or 数ドル）
  ↓
[Cloud SQL db-f1-micro]（$7.67/月）
```

**月額**: $7.67〜

---

### Cloud Run デプロイ手順

#### ステップ1: gcloud CLI インストール

```bash
# Windows
# https://cloud.google.com/sdk/docs/install からインストーラーをダウンロード

# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
```

#### ステップ2: 認証とプロジェクト設定

```bash
# Google アカウントで認証
gcloud auth login

# プロジェクト作成
gcloud projects create trail-condition-portal --name="Trail Condition Portal"

# プロジェクト設定
gcloud config set project trail-condition-portal

# APIを有効化
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

---

#### ステップ3: Dockerfile.cloudrun を作成

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

# 静的ファイルを収集
RUN uv run manage.py collectstatic --noinput

# Cloud Run はポート 8080 を期待
ENV PORT=8080

# Gunicorn で起動
CMD uv run gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120
```

**重要**: Cloud Run は環境変数 `PORT` でポート番号を指定します（通常8080）。

---

#### ステップ4: Cloud SQL インスタンス作成

```bash
# PostgreSQL インスタンス作成（db-f1-micro: 最小・最安）
gcloud sql instances create trail-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=asia-northeast1 \
    --storage-size=10GB \
    --storage-type=HDD

# データベース作成
gcloud sql databases create trail_condition --instance=trail-db

# ユーザー作成
gcloud sql users create trail_user \
    --instance=trail-db \
    --password=YOUR_STRONG_PASSWORD
```

**料金**: $7.67/月（db-f1-micro）

---

#### ステップ5: Cloud Run にデプロイ

```bash
# Artifact Registry にリポジトリ作成（初回のみ）
gcloud artifacts repositories create trail-condition-repo \
    --repository-format=docker \
    --location=asia-northeast1

# Docker イメージをビルド＆プッシュ
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/trail-condition-portal/trail-condition-repo/web

# Cloud Run にデプロイ
gcloud run deploy trail-condition \
    --image asia-northeast1-docker.pkg.dev/trail-condition-portal/trail-condition-repo/web \
    --platform managed \
    --region asia-northeast1 \
    --allow-unauthenticated \
    --set-env-vars "DJANGO_SECRET_KEY=YOUR_SECRET_KEY" \
    --set-env-vars "DJANGO_DEBUG=False" \
    --set-env-vars "ALLOWED_HOSTS=.run.app" \
    --add-cloudsql-instances trail-condition-portal:asia-northeast1:trail-db \
    --set-env-vars "DATABASE_URL=postgresql://trail_user:YOUR_PASSWORD@/trail_condition?host=/cloudsql/trail-condition-portal:asia-northeast1:trail-db"
```

**デプロイ完了！**

Cloud Run が自動的に URL を発行：
```
https://trail-condition-xxxx-an.a.run.app
```

---

#### ステップ6: カスタムドメイン設定

##### Cloud Run のドメインマッピング

```bash
# ドメインマッピング作成
gcloud run domain-mappings create \
    --service trail-condition \
    --domain trail-condition.com \
    --region asia-northeast1
```

指示に従って DNS レコードを設定（A, AAAA レコード）

##### または Cloudflare を使う（推奨）

Cloudflare で CNAME レコードを追加：

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| CNAME | @ | trail-condition-xxxx-an.a.run.app | Proxied |

**メリット**:
- Cloudflare の CDN + DDoS 対策が使える
- Cloud Run の URL を隠せる
- 柔軟な設定

---

#### ステップ7: マイグレーション実行

```bash
# Cloud Run のコンテナ内でコマンド実行
gcloud run services update trail-condition \
    --region asia-northeast1 \
    --command "uv,run,manage.py,migrate"

# または Cloud Run Jobs を使う（推奨）
gcloud run jobs create migrate-db \
    --image asia-northeast1-docker.pkg.dev/trail-condition-portal/trail-condition-repo/web \
    --region asia-northeast1 \
    --add-cloudsql-instances trail-condition-portal:asia-northeast1:trail-db \
    --set-env-vars "DATABASE_URL=..." \
    --command "uv,run,manage.py,migrate"

# ジョブ実行
gcloud run jobs execute migrate-db --region asia-northeast1
```

---

#### ステップ8: 定期実行（trail_sync）の設定

Cloud Scheduler + Cloud Run Jobs を使用

```bash
# trail_sync ジョブ作成
gcloud run jobs create trail-sync \
    --image asia-northeast1-docker.pkg.dev/trail-condition-portal/trail-condition-repo/web \
    --region asia-northeast1 \
    --add-cloudsql-instances trail-condition-portal:asia-northeast1:trail-db \
    --set-env-vars "DATABASE_URL=..." \
    --set-env-vars "DEEPSEEK_API_KEY=..." \
    --set-env-vars "GEMINI_API_KEY=..." \
    --command "uv,run,manage.py,trail_sync"

# Cloud Scheduler で定期実行（毎日午前9時）
gcloud scheduler jobs create http trail-sync-daily \
    --location asia-northeast1 \
    --schedule "0 9 * * *" \
    --uri "https://asia-northeast1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/trail-condition-portal/jobs/trail-sync:run" \
    --http-method POST \
    --oauth-service-account-email YOUR_SERVICE_ACCOUNT@trail-condition-portal.iam.gserviceaccount.com
```

---

### Cloud Run のコスト最適化

#### 1. メモリとCPUの最適化

```bash
# メモリを256MBに（デフォルト512MB）
gcloud run services update trail-condition \
    --memory 256Mi \
    --cpu 1
```

#### 2. 最小インスタンス数を0に（デフォルト）

```bash
# リクエストがない時は完全に停止（コスト0）
gcloud run services update trail-condition \
    --min-instances 0
```

**注意**: 初回アクセス時に**コールドスタート**（数秒の遅延）が発生

#### 3. タイムアウトの調整

```bash
# タイムアウトを60秒に（デフォルト300秒）
gcloud run services update trail-condition \
    --timeout 60s
```

---

## 構成パターン別コスト比較

### パターン 1: VPS + WhiteNoise + Cloudflare

```
[Cloudflare]（無料）
  ↓
[VPS: Docker]（$5〜10/月）
  ├─ Gunicorn + WhiteNoise
  └─ PostgreSQL
```

| 項目 | 月額コスト |
|------|-----------|
| VPS（ConoHa 2GB） | ¥1,000 ($7) |
| Cloudflare | 無料 |
| **合計** | **¥1,000** |

**メリット**:
- シンプル
- 固定費
- フルコントロール

---

### パターン 2: VPS + nginx + Let's Encrypt

```
[VPS: Docker]（$5〜10/月）
  ├─ nginx（SSL終端）
  ├─ Gunicorn
  └─ PostgreSQL
```

| 項目 | 月額コスト |
|------|-----------|
| VPS | ¥1,000 ($7) |
| **合計** | **¥1,000** |

**メリット**:
- Cloudflare 不要
- 自己完結
- nginx の制御

---

### パターン 3: Cloud Run + Cloud SQL + Cloudflare

```
[Cloudflare]（無料）
  ↓
[Cloud Run]（無料枠 or 従量）
  ↓
[Cloud SQL]（$7.67/月〜）
```

| 項目 | 月額コスト |
|------|-----------|
| Cloud Run（小規模） | 無料枠内 |
| Cloud SQL db-f1-micro | $7.67 |
| Cloudflare | 無料 |
| **合計** | **$7.67** |

**メリット**:
- フルマネージド
- オートスケール
- メンテナンス不要

---

### パターン 4: Cloud Run + Supabase + Cloudflare（最安構成）

```
[Cloudflare]（無料）
  ↓
[Cloud Run]（無料枠）
  ↓
[Supabase PostgreSQL]（無料）
```

| 項目 | 月額コスト |
|------|-----------|
| Cloud Run | 無料枠内 |
| Supabase | 無料（500MB、2週間非アクティブで停止） |
| Cloudflare | 無料 |
| **合計** | **$0** |

**メリット**:
- 完全無料（小規模）
- フルマネージド

**デメリット**:
- データベース容量制限
- 非アクティブで停止

---

### パターン 5: AWS EC2 + ALB + RDS

```
[AWS ALB]（SSL終端、$16/月）
  ↓
[EC2 t3.micro]（$7.5/月）
  ├─ Gunicorn + WhiteNoise
[RDS db.t3.micro]（$15/月）
```

| 項目 | 月額コスト |
|------|-----------|
| ALB | $16 |
| EC2 t3.micro | $7.5 |
| RDS db.t3.micro | $15 |
| **合計** | **$38.5** |

**高い！**（小規模には不向き）

---

## 推奨デプロイ構成（規模別）

### 個人プロジェクト・小規模（月間 1万PV以下）

#### 推奨: **VPS + WhiteNoise + Cloudflare**

**月額**: ¥1,000

**理由**:
- シンプル
- 固定費で予測可能
- Dockerで簡単デプロイ

**手順**:
1. ConoHa VPS（2GB）契約
2. Docker インストール
3. `docker-compose.prod.yml` でデプロイ
4. Cloudflare で DNS + SSL 設定

**所要時間**: 1時間

---

### 中規模（月間 1万〜10万PV）

#### 推奨: **VPS + nginx + Let's Encrypt**

または

#### 推奨: **Cloud Run + Cloud SQL + Cloudflare**

**月額**: ¥1,000〜$20

**理由**:
- VPS: nginx で静的ファイル配信を最適化
- Cloud Run: オートスケールでトラフィック変動に対応

---

### 大規模（月間 10万PV以上）

#### 推奨: **Cloud Run + Cloud SQL + Cloudflare + Cloud CDN**

**月額**: $30〜

**理由**:
- オートスケール
- グローバル配信
- 高可用性

---

## まとめ

### リバースプロキシの役割

- **nginx**: サーバー内でのSSL終端、静的ファイル配信、プロキシ
- **Cloudflare**: グローバルCDN、DDoS対策、SSL自動管理

### コンテナ間通信

- Docker内部ネットワークでサービス名で通信
- SSL終端後はHTTP通信でOK（同じマシン内）
- `ports` で外部公開、`expose` で内部のみ

### Cloud Run

- 無料枠が大きい（月200万リクエスト）
- Cloud SQLは有料（$7.67/月〜）
- 小規模なら Supabase 等の外部DB推奨

### コスト最適化

- 小規模: VPS + Cloudflare（¥1,000/月）
- 無料で始めたい: Cloud Run + Supabase（$0）
- 中〜大規模: Cloud Run + Cloud SQL（$7.67〜）

---

**作成日**: 2026-01-16
**最終更新**: 2026-01-16
