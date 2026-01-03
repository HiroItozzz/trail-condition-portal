```
# 1. 必要なファイルを作成
touch pyproject.toml uv.lock .env .dockerignore

# 2. docker-compose起動
docker-compose up -d --build

# 3. マイグレーション（初回）
docker-compose exec web uv run python manage.py migrate

# 4. スーパーユーザー作成
docker-compose exec web uv run python manage.py createsuperuser

# 5. 開発中のよく使うコマンド
# シェルに入る
docker-compose exec web bash

# マイグレーション作成
docker-compose exec web uv run python manage.py makemigrations

# シェルを開く
docker-compose exec web uv run python manage.py shell

# テスト
docker-compose exec web uv run python manage.py test
```
