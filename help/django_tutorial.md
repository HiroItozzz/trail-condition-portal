# Django 基本チュートリアル（インストール〜最初のアプリ作成）
## 1. Djangoのインストール

### 仮想環境の確認と有効化

```powershell
# 現在の仮想環境を確認
(trail-condition-search) PS E:\...>
```

```powershell
# 仮想環境が有効でない場合は：

# 1. 仮想環境を作成（既にあるかも）
python -m venv venv

# 2. 仮想環境を有効化
# PowerShellの場合：
.\venv\Scripts\Activate.ps1

# コマンドプロンプトの場合：
venv\Scripts\activate
```

### Djangoのインストール

```powershell
# pipが最新か確認
python -m pip install --upgrade pip

# Djangoをインストール（LTS推奨）
pip install django

# バージョン確認
python -m django --version

# 例：
# 5.0.3 などと表示されればOK
```

---

## 2. 基本的なDjangoプロジェクトの作成

### プロジェクト構成を理解

```text
trail-condition-portal/     # プロジェクトルート
├── manage.py              # Django管理スクリプト
├── config/                # プロジェクト設定（任意の名前）
│   ├── __init__.py
│   ├── settings.py       # 全設定
│   ├── urls.py           # URLルーティング
│   ├── asgi.py           # ASGI設定
│   └── wsgi.py           # WSGI設定
└── [各アプリディレクトリ]
```

### プロジェクト作成手順

```powershell
# 1. まず現在のディレクトリを整理
# （FastAPIのファイルを移動）
mkdir archive

# FastAPI関連ファイルをarchiveに移動
move app.py archive/ -ErrorAction SilentlyContinue
move requirements.txt archive/requirements_fastapi.txt

# 2. Djangoプロジェクトを作成

# 方法A: 現在のディレクトリに作成
django-admin startproject config .

# 方法B: 新しいプロジェクトとして作成（おすすめ）
# cd ..
# django-admin startproject trail_portal
# cd trail_portal

# 3. プロジェクト構造を確認
Get-ChildItem -Recurse
```

---

## 3. 基本的な設定

### settings.py の最小限の設定

```python
# config/settings.py

import os
from pathlib import Path

# ベースディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent

# セキュリティキー（本番では環境変数から）
SECRET_KEY = 'django-insecure-一時的なキー-開発用'

# デバッグモード（開発中はTrue）
DEBUG = True

# 許可するホスト
ALLOWED_HOSTS = []

# インストールするアプリ
INSTALLED_APPS = [
    'django.contrib.admin',      # 管理サイト
    'django.contrib.auth',       # 認証システム
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# ミドルウェア
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URL設定
ROOT_URLCONF = 'config.urls'

# テンプレート設定
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGIアプリケーション
WSGI_APPLICATION = 'config.wsgi.application'
```

---

## 4. データベース設定

### デフォルト（SQLite）のまま始める

```python
# config/settings.py のデータベース設定

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # SQLiteファイル
    }
}
```

### 初期マイグレーションの実行

```powershell
# データベースマイグレーション（テーブル作成）
python manage.py migrate

# 実行結果例：
# Operations to perform:
#   Apply all migrations: admin, auth, contenttypes, sessions
# Running migrations:
#   Applying contenttypes.0001_initial... OK
#   Applying auth.0001_initial... OK
#   ...（略）
```

---

## 5. 管理ユーザー作成

```powershell
# スーパーユーザー（管理者）作成
python manage.py createsuperuser

# 対話的に設定：
# Username: admin
# Email address: （任意、空でもOK）
# Password: （入力）
# Password (again): （確認）

# 例：
# Superuser created successfully.
```

---

## 6. 開発サーバーの起動

```powershell
# 開発サーバーを起動
python manage.py runserver

# 出力例：
# Watching for file changes with StatReloader
# Performing system checks...
# System check identified no issues (0 silenced).
# Django version 5.0.3, using settings 'config.settings'
# Starting development server at http://127.0.0.1:8000/
# Quit the server with CTRL-BREAK.
```

```text
# ブラウザで確認
http://127.0.0.1:8000/
→ "The install worked successfully! Congratulations!" と表示されればOK

http://127.0.0.1:8000/admin/
→ 管理画面
```

---

## 7. 最初のアプリ作成

### 登山道情報アプリを作成

```powershell
# アプリ作成（trails: 登山道情報用）
python manage.py startapp trails

# 作成されるファイル：
# trails/
# ├── __init__.py
# ├── admin.py        # 管理画面設定
# ├── apps.py         # アプリ設定
# ├── models.py       # データモデル
# ├── tests.py        # テスト
# └── views.py        # ビュー（処理）
```

### アプリを登録

```python
# config/settings.py の INSTALLED_APPS に追加

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ... 他のデフォルトアプリ ...
    'trails',  # ← 追加
]
```

---

## 8. 基本的なモデル作成

```python
# trails/models.py
from django.db import models

class Trail(models.Model):
    """登山道モデル"""

    # 難易度の選択肢
    DIFFICULTY_CHOICES = [
        ('easy', '初級'),
        ('medium', '中級'),
        ('hard', '上級'),
    ]

    # フィールド定義
    name = models.CharField('登山道名', max_length=200)
    prefecture = models.CharField('都道府県', max_length=20)
    difficulty = models.CharField('難易度', max_length=10, choices=DIFFICULTY_CHOICES)
    length_km = models.FloatField('距離(km)')
    elevation_gain = models.IntegerField('累積標高(m)')
    description = models.TextField('説明', blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.prefecture})"
```

---

## 9. モデルをデータベースに反映

```powershell
# モデル変更を検出
python manage.py makemigrations trails

# 出力例：
# Migrations for 'trails':
#   trails/migrations/0001_initial.py
#     - Create model Trail

# マイグレーションを適用
python manage.py migrate
```

---

## 10. 管理画面にモデルを登録

```python
# trails/admin.py
from django.contrib import admin
from .models import Trail

@admin.register(Trail)
class TrailAdmin(admin.ModelAdmin):
    """登山道管理画面"""
    list_display = ('name', 'prefecture', 'difficulty', 'length_km')
    list_filter = ('prefecture', 'difficulty')
    search_fields = ('name', 'prefecture')
```

---

## 11. 基本的なビュー作成

```python
# trails/views.py
from django.shortcuts import render, get_object_or_404
from .models import Trail

def trail_list(request):
    """登山道一覧"""
    trails = Trail.objects.all()
    return render(request, 'trails/list.html', {'trails': trails})

def trail_detail(request, trail_id):
    """登山道詳細"""
    trail = get_object_or_404(Trail, id=trail_id)
    return render(request, 'trails/detail.html', {'trail': trail})
```

---

## 12. URL設定

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('trails.urls')),  # trailsアプリのURL
]
```

```python
# trails/urls.py（新規作成）
from django.urls import path
from . import views

urlpatterns = [
    path('trails/', views.trail_list, name='trail_list'),
    path('trails/<int:trail_id>/', views.trail_detail, name='trail_detail'),
]
```

---

## 13. テンプレート作成

```html
<!-- trails/templates/trails/list.html -->
<!DOCTYPE html>
<html>
<head>
    <title>登山道一覧</title>
</head>
<body>
    <h1>登山道一覧</h1>
    <ul>
    {% for trail in trails %}
        <li>
            <a href="{% url 'trail_detail' trail.id %}">
                {{ trail.name }} ({{ trail.prefecture }})
            </a>
            - {{ trail.difficulty }}
        </li>
    {% empty %}
        <li>登山道が登録されていません</li>
    {% endfor %}
    </ul>
</body>
</html>
```

---

## 14. 全体の作業フローまとめ

```powershell
# 1. 仮想環境設定
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Djangoインストール
pip install django

# 3. プロジェクト作成
django-admin startproject config .

# 4. データベース設定
python manage.py migrate

# 5. 管理者作成
python manage.py createsuperuser

# 6. アプリ作成
python manage.py startapp trails

# 7. マイグレーション
python manage.py makemigrations
python manage.py migrate

# 8. サーバー起動
python manage.py runserver
```

---

## 15. トラブルシューティング

```powershell
# django-admin コマンドが認識されない場合
python -m django startproject config .

# PowerShellで実行ポリシー変更（初回のみ）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
